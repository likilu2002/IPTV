import os
import requests
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 使用 os.path 来获取当前脚本的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_file_path = os.path.join(current_dir, 'config.json')

def get_json_config():
    """
    从 JSON 文件获取配置信息。
    """
    try:
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
        timeout = config.get('timeout', 3)  # 默认超时30秒
        max_workers = config.get('max_workers', 20)  # 默认最大线程数20
        output_path = config.get('output_path', 'iptv.m3u')  # 默认输出路径
        m3u_urls = config.get('m3u_urls', [])
        return timeout, max_workers, output_path, m3u_urls
    except FileNotFoundError:
        logging.error(f"配置文件未找到：{config_file_path}")
        raise
    except json.JSONDecodeError:
        logging.error(f"配置文件 {config_file_path} 格式错误")
        raise

def download_m3u_content(url, timeout):
    """
    下载m3u文件内容，确保使用utf-8编码
    """
    logging.info(f"开始下载m3u文件: {url}")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        response.encoding = 'utf-8'  # 强制使用utf-8编码
        return response.text
    except requests.RequestException as e:
        logging.error(f"下载或解析m3u文件出错: {e}")
        return None

def test_link_speed(url, timeout):
    """
    测试特定链接的速度。
    """
    try:
        start_time = time.time()
        with requests.get(url, timeout=timeout, stream=True) as response:
            response.raise_for_status()  # 确保请求成功
            chunk_size = 1024  # 读取1024字节的数据
            for _ in response.iter_content(chunk_size=chunk_size):
                break  # 只读取首部分数据即可
            end_time = time.time()
            return end_time - start_time
    except requests.RequestException:
        return float('inf')

def test_link_speed_concurrent(urls, timeout, max_workers):
    """
    并发测试给定URL列表的响应速度。
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(test_link_speed, url, timeout): url for url in urls}
        results = {}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception as e:
                logging.error(f"测试链接速度异常: {url}, 错误: {e}")
                results[url] = float('inf')
    return results

def parse_m3u_content(content):
    """
    解析m3u文件内容
    """
    logging.info("开始解析m3u文件内容...")
    channels = {}
    lines = content.split('\n')
    for i in range(len(lines)):
        if lines[i].startswith('#EXTINF:'):
            # 更严格的分割方法，确保正确分割属性
            parts = lines[i].split(',', 1)
            if len(parts) > 1:
                info_part = parts[0]
                display_name = parts[1].strip()

                channel_info = {}
                attributes = info_part.split(' ')
                for attr in attributes:
                    if '=' in attr:
                        key, value = attr.split('=', 1)
                        value = value.strip('"')
                        # 确保不会覆盖已有的属性值（避免使用最后一个定义）
                        if key not in channel_info or not channel_info[key]:
                            channel_info[key] = value

                identifier = channel_info.get('tvg-name', display_name if display_name else channel_info.get('tvg-id', '未知频道'))
                tvg_name = channel_info.get('tvg-name', display_name if display_name else channel_info.get('tvg-id'))

                group_title = channel_info.get('group-title', '其他频道')
                if not group_title:
                    group_title = '其他频道'

                if identifier and i + 1 < len(lines) and lines[i+1].startswith('http'):
                    channel_url = lines[i + 1].strip()
                    if identifier not in channels:
                        channels[identifier] = {
                            'urls': [],
                            'group_title': group_title,
                            'display_name': identifier,
                            'tvg_name': tvg_name
                        }
                    channels[identifier]['urls'].append(channel_url)
    return channels

def select_fastest_links(channels, timeout, max_workers):
    """
    测试链接速度并选择每个频道最快的链接。
    """
    logging.info("开始测试链接速度并选择最快的链接...")
    fastest_links = {}
    for identifier, info in channels.items():
        group_title = info['group_title']
        logging.info(f"正在测试 {identifier} ({group_title}) 的链接...")
        url_speeds = test_link_speed_concurrent(info['urls'], timeout, max_workers)
        best_url, best_speed = min(url_speeds.items(), key=lambda x: x[1])
        if best_speed != float('inf'):
            logging.info(f"为 {identifier} ({group_title}) 选择最快链接: {best_url}\n")
            fastest_links[identifier] = {'url': best_url, 'group_title': group_title}
        else:
            logging.warning(f"{identifier} ({group_title}) 的所有链接均无法访问，已跳过。\n")
    return fastest_links

def create_new_m3u(fastest_links, output_path):
    """
    生成包含每个频道最快链接的新m3u文件。
    """
    logging.info(f"生成新的m3u文件: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write('#EXTM3U\n')
        for identifier, info in fastest_links.items():
            url = info['url']
            group_title = info['group_title']
            # 格式化每条记录，只包含 group-title 和频道名称
            file.write(f'#EXTINF:-1 group-title="{group_title}",{identifier}\n{url}\n')
    logging.info("完成。")


# 执行脚本
def main():
    timeout, max_workers, output_path, m3u_urls = get_json_config()

    all_channels = {}
    for url in m3u_urls:
        content = download_m3u_content(url, timeout)
        if content:
            channels = parse_m3u_content(content)
            for identifier, info in channels.items():
                if identifier not in all_channels:
                    all_channels[identifier] = {'urls': [], 'group_title': info['group_title']}
                all_channels[identifier]['urls'].extend(info['urls'])

    fastest_links = select_fastest_links(all_channels, timeout, max_workers)
    create_new_m3u(fastest_links, output_path)

if __name__ == "__main__":
    main()