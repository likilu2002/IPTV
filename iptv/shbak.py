import requests
from bs4 import BeautifulSoup
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import select
import sys
import subprocess
import colorama
from colorama import Fore, Style
import base64
colorama.init(autoreset=True)

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_public_ip():
    ipv4_regex = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
    try:
        response = requests.get('http://ipinfo.io/ip')
        response.raise_for_status()
        ip = response.text.strip()
        if re.match(ipv4_regex, ip):
            logging.info(f"当前服务器的外网 IPv4 地址: {ip}")
            return ip
        else:
            logging.error(f"ipinfo.io 返回的 IP 也不是 IPv4: {ip}")
    except Exception as e:
        logging.error(f"获取外网 IP 时发生错误: {e}")
    return None

def check_first_link(filename):
    try:
        logging.info("正在检查m3u文件中的第一条链接...")
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('http://'):
                    url = line.strip()
                    logging.info(f"测试链接: {url}")
                    try:
                        start_time = time.time()
                        with requests.get(url, timeout=5, stream=True) as response:
                            response.raise_for_status()
                            for _ in response.iter_content(1024):
                                break
                            response_time = time.time() - start_time
                            logging.info(f"当前m3u文件播放正常, 响应时间: {response_time:.2f}秒")
                            return True
                    except requests.exceptions.Timeout:
                        logging.error("请求超时，链接响应太慢。")
                    except Exception as e:
                        logging.error(f"测试链接时出错: {e}")
                    break
    except Exception as e:
        logging.error(f"检查链接时出错: {e}")
    return False

def fetch_ips_from_fofa(max_results=20, ip_head="222", full_search=False):
    api_url = 'https://fofa.info/api/v1/search/all'
    email = 'likilu@gmail.com'
    api_key = 'd6ff30645e40c27734cd7622b3649fe0'
    
    if full_search:
        query = f'country="CN" && city="Shanghai" && "udpxy" && org="China Telecom Group"'
    else:
        query = f'country="CN" && city="Shanghai" && "udpxy" && org="China Telecom Group" && ip="{ip_head}.0.0.0/8"'
    
    params = {
        'email': email,
        'key': api_key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'size': max_results,
        'fields': 'host,port'
    }
    
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        result = response.json()
        ip_ports = []
        
        for item in result.get('results', []):
            ip = item[0]
            port = item[1]
            if ip and port:
                ip_port = f"{ip}:{port}"
                if re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', ip_port):
                    ip_ports.append(ip_port)
        
        logging.info(f"从 Fofa 获取的 IP 地址和端口: {ip_ports}")
        return ip_ports
    except Exception as e:
        logging.error(f"使用 Fofa API 抓取 IP 和端口时出错: {e}")
        return []

def fetch_ips_from_quake(api_key, ip_head, full_search=False):
    url = 'https://quake.360.net/api/v3/search/quake_service'
    headers = {
        'X-QuakeToken': '531d244b-ae40-46df-8afb-164611e3a0dd',
        'Content-Type': 'application/json'
    }
    if full_search:
        query = f'isp:"中国电信" AND city:"Shanghai City" AND app:"udpxy multicast UDP-to-HTTP"'
    else:
        query = f'isp:"中国电信" AND city:"Shanghai City" AND app:"udpxy multicast UDP-to-HTTP" AND ip:"{ip_head}.0.0.0/8"'
    
    data = {
        "query": query,
        "start": 0,
        "size": 20
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        ip_ports = []
        
        for item in result.get('data', []):
            ip = item.get('ip')
            port = item.get('port')
            if ip and port:
                ip_port = f"{ip}:{port}"
                if re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', ip_port):
                    ip_ports.append(ip_port)
        
        logging.info(f"从 Quake 获取的 IP 地址和端口: {ip_ports}")
        return ip_ports
    except Exception as e:
        logging.error(f"使用 Quake API 抓取 IP 和端口时出错: {e}")
        return []

def test_ip_speed(ip_port, timeout=1):
    ip, port = ip_port.split(':')
    url = f'http://{ip}:{port}/udp/239.45.3.112:5140'
    logging.info(f"正在测试链接: {url}")
    try:
        start_time = time.time()
        with requests.get(url, timeout=timeout, stream=True) as response:
            response.raise_for_status()  # 确认响应状态是 '200 OK'
            for _ in response.iter_content(1024):  # 读取一些内容来验证链接活性
                break
            response_time = time.time() - start_time
            logging.info(f"完成测试: {ip_port}, 响应时间为 {response_time:.2f} 秒")
            return ip_port, response_time, "success"
    except requests.exceptions.Timeout:
        logging.warning(f"超时: {ip_port} 响应过慢")
        return ip_port, float('inf'), "timeout"
    except requests.exceptions.ConnectionError:
        logging.error(f"连接被拒绝: {ip_port}")
        return ip_port, float('inf'), "connection_refused"
    except Exception as e:
        logging.error(f"测试 {ip_port} 时发生未知错误: {e}")
        return ip_port, float('inf'), "other_error"

def speed_test_ips(ips):
    best_ip = None
    best_time = float('inf')
    logging.info("开始进行IP响应速度测试...")

    # 统计信息
    total_tested = 0
    success_count = 0
    timeout_count = 0
    connection_refused_count = 0
    other_error_count = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_ip_speed, ip): ip for ip in ips}
        for future in as_completed(futures):
            ip, time_taken, result = future.result()
            total_tested += 1
            if result == "success":
                success_count += 1
                if time_taken < best_time:
                    best_time = time_taken
                    best_ip = ip
            elif result == "timeout":
                timeout_count += 1
            elif result == "connection_refused":
                connection_refused_count += 1
            elif result == "other_error":
                other_error_count += 1

    # 输出统计信息
    logging.info(f"测速完成，总共测试: {total_tested} 个IP")
    logging.info(f"成功测速: {success_count} 个IP")
    logging.info(f"超时的IP: {timeout_count} 个")
    logging.info(f"连接被拒绝的IP: {connection_refused_count} 个")
    logging.info(f"其他错误: {other_error_count} 个")

    if best_ip:
        logging.info(f"响应时间最快的IP是: {best_ip}")
    else:
        logging.error("没有找到响应时间足够快的IP。")
    return best_ip

def prompt_for_full_search():
    print("当前获取的IP数量较少，是否进行全IP搜索？（输入y进行全IP搜索，8秒内无输入则跳过）:")
    user_choice = None
    start_time = time.time()
    while True:
        ready, _, _ = select.select([sys.stdin], [], [], 8)
        if ready:
            user_choice = sys.stdin.readline().strip().lower()
            if user_choice == 'y':
                return True
            break
        if (time.time() - start_time) >= 8:
            break
    return False

def update_m3u_file(filename, best_ip_port):
    try:
        with open(filename, 'r') as file:
            content = file.read()

        ip_pattern = re.compile(r'http://\d+\.\d+\.\d+\.\d+:\d+')
        updated_content = ip_pattern.sub(f'http://{best_ip_port}', content)
        
        with open(filename, 'w') as file:
            file.write(updated_content)
        
        logging.info(f"{Fore.GREEN}m3u文件已成功更新，所有IP及端口已替换为最快的IP及端口: {best_ip_port}")
        subprocess.run(["python3", "/var/www/html/iptv/iptv.py"])
    except Exception as e:
        logging.error(f"更新 m3u 文件时发生错误: {e}")

def fetch_and_test_ips(m3u_file, api_key):
    public_ip = get_public_ip()  # 获取外网 IP
    if public_ip:
        ip_head = public_ip.split(".")[0]
        ips1 = fetch_ips_from_quake(api_key, ip_head)
        ips2 = fetch_ips_from_fofa(max_results=20, ip_head=ip_head)
        all_ips = list(set(ips1 + ips2))
        logging.info(f"去重后的唯一IP地址列表: {all_ips}")
        
        best_ip = speed_test_ips(all_ips)
        
        if not best_ip:
            if prompt_for_full_search():
                ips1 = fetch_ips_from_quake(api_key, ip_head, full_search=True)
                ips2 = fetch_ips_from_fofa(max_results=20, ip_head=ip_head, full_search=True)
                all_ips = list(set(ips1 + ips2))
                logging.info(f"全IP搜索后得到的唯一IP地址列表: {all_ips}")
                best_ip = speed_test_ips(all_ips)

        if best_ip:
            logging.info(f"最佳 IP 地址: {best_ip}")
            update_m3u_file(m3u_file, best_ip)
        else:
            logging.error("没有找到有效的 IP 地址用于更新 M3U 文件")
    else:
        logging.error("未能获取到服务器的外网 IP")

def main():
    m3u_file = '/var/www/html/iptv/sh.m3u'
    api_key = "531d244b-ae40-46df-8afb-164611e3a0dd"
    print("请选择操作：")
    print("1 - 测试第一个链接")
    print("2 - 跳过测试链接，直接抓取 IP")
    choice = input(f"输入您的选择（默认选择1）: ").strip()
    if choice == '2':
        fetch_and_test_ips(m3u_file, api_key)
    else:
        if not check_first_link(m3u_file):
            print("第一个链接测试失败，继续抓取IP...")
            fetch_and_test_ips(m3u_file, api_key)
        else:
            print("第一个链接测试成功，无需进一步操作。")

if __name__ == '__main__':
    main()