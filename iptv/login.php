<?php
// 开启会话
session_start();

// 定义登录凭据（可以替换为数据库查询等方式）
$valid_username = 'likilu';  // 请替换为您的用户名
$valid_password = 'cao2maliki';  // 请替换为您的密码

// 处理用户登录
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 获取用户输入的用户名和密码
    $username = $_POST['username'];
    $password = $_POST['password'];
    
    // 验证用户名和密码
    if ($username === $valid_username && $password === $valid_password) {
        // 登录成功，设置 session 和 cookie
        $_SESSION['logged_in'] = true;
        setcookie('logged_in', true, time() + (86400 * 30), "/");
        
        // 重定向到配置页面
        header('Location: config.php');
        exit();
    } else {
        $login_error = "用户名或密码错误，请重试。";
    }
}

// 如果用户已登录，并且当前页面不是登录页面，直接重定向到 config.php
if ((isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true) || 
    (isset($_COOKIE['logged_in']) && $_COOKIE['logged_in'] === 'true')) {
    // 判断当前页面是否已经是 config.php，以防止循环重定向
    if (basename($_SERVER['PHP_SELF']) !== 'config.php') {
        header('Location: config.php');
        exit();
    }
}
?>

<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 400px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            margin-top: 100px;
        }
        h1 {
            font-size: 24px;
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 10px;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 8px;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        input[type="submit"] {
            padding: 10px 15px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #218838;
        }
        .error {
            color: red;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>登录</h1>
        <?php if (isset($login_error)) echo "<p class='error'>$login_error</p>"; ?>
        <form action="login.php" method="POST">
            <label for="username">用户名:</label>
            <input type="text" name="username" id="username" required>

            <label for="password">密码:</label>
            <input type="password" name="password" id="password" required>

            <input type="submit" value="登录">
        </form>
    </div>
</body>
</html>