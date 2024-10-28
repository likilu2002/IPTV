<?php
// 开启会话，用于登录状态管理
session_start();

// 定义 JSON 配置文件路径
$config_file = './config.json';

// 检查是否已经登录
if (!isset($_SESSION['logged_in'])) {
    // 如果未登录，跳转到登录页面
    header('Location: login.php');
    exit();
}

// 如果表单提交，处理并更新 JSON 配置
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['update_config'])) {
    // 获取表单提交的值
    $timeout = $_POST['timeout'];
    $max_workers = $_POST['max_workers'];
    $output_path = $_POST['output_path'];

    // 对每个 URL 使用 trim() 来去除空格和多余字符
    $m3u_urls = array_map('trim', array_filter($_POST['m3u_urls'], 'strlen'));

    // 重新组织 JSON 数据
    $config = [
        'timeout' => intval($timeout),
        'max_workers' => intval($max_workers),
        'output_path' => $output_path,
        'm3u_urls' => $m3u_urls
    ];

    // 写回 JSON 文件，避免转义斜杠
    if (file_put_contents($config_file, json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES))) {
        echo "配置已更新！";
    } else {
        echo "配置更新失败！请检查文件权限。";
    }
}

// 读取 JSON 文件中的配置信息
$config = json_decode(file_get_contents($config_file), true);
?>

<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV 配置管理</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        h1 {
            font-size: 24px;
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 10px;
        }
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 8px;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button, input[type="submit"] {
            padding: 10px 15px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover, input[type="submit"]:hover {
            background-color: #218838;
        }
        .url-container {
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }
        .url-container input[type="text"] {
            flex: 1;
        }
        .url-container button {
            margin-left: 10px;
            background-color: #dc3545;
        }
        button:hover {
            background-color: #c82333;
        }
        .logout {
            background-color: #dc3545;
            color: white;
        }
        .logout:hover {
            background-color: #c82333;
        }
        /* 调整按钮组排成一行 */
        .button-group {
            display: flex;
            justify-content: flex-start;
            gap: 10px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>当前配置</h1>         
        <!-- 更新配置的表单 -->
        <form action="" method="POST">
            <label for="timeout">Timeout (秒):</label>
            <input type="number" id="timeout" name="timeout" value="<?= $config['timeout'] ?>" required>

            <label for="max_workers">Max Workers:</label>
            <input type="number" id="max_workers" name="max_workers" value="<?= $config['max_workers'] ?>" required>

            <label for="output_path">Output Path:</label>
            <input type="text" id="output_path" name="output_path" value="<?= $config['output_path'] ?>" required>

            <h2>M3U URL 列表</h2>
            <div id="url-list">
                <?php foreach ($config['m3u_urls'] as $url): ?>
                    <div class="url-container">
                        <input type="text" name="m3u_urls[]" value="<?= $url ?>">
                        <button type="button" onclick="removeUrl(this)">删除</button>
                    </div>
                <?php endforeach; ?>
            </div>

            <!-- 将按钮组放在同一行 -->
            <div class="button-group">
                <button type="button" onclick="addUrl()">添加新 URL</button>
                <input type="submit" name="update_config" value="更新配置">
            </div>
        </form>

        <!-- 独立的登出按钮表单 -->
        <form action="logout.php" method="POST" class="button-group">
            <input type="submit" value="登出" class="logout">
        </form>

    </div>

    <script>
        function addUrl() {
            const urlList = document.getElementById('url-list');
            const newUrlDiv = document.createElement('div');
            newUrlDiv.className = 'url-container';
            newUrlDiv.innerHTML = '<input type="text" name="m3u_urls[]" placeholder="请输入新 URL"><button type="button" onclick="removeUrl(this)">删除</button>';
            urlList.appendChild(newUrlDiv);
        }

        function removeUrl(button) {
            button.parentElement.remove();
        }
    </script>
</body>
</html>
