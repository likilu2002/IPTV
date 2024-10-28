<?php
// 开启会话
session_start();

// 清除 session 和 cookie
session_unset();
session_destroy();
setcookie('logged_in', '', time() - 3600, "/"); // 删除 cookie

// 重定向到登录页面
header('Location: login.php');
exit();
?>
