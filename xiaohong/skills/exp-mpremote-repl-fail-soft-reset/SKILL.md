---
name: exp-mpremote-repl-fail-soft-reset
description: 当 repl_exec 报 mpremote connect /dev/tty 错误时，先 soft_reset 再重试的恢复流程
---

## 现象
repl_exec 执行失败，报错 `Error executing tool repl_exec: Command '['mpremote', 'connect', '/dev/tty...'`（串口连接被占用/挂起）。

## 原因
前一次 REPL 会话或运行中的脚本未正常释放串口，mpremote 无法建立新连接。常见于：脚本死循环、上次会话异常断开、upload 后未复位。

## 应对步骤
1. 调用 `soft_reset` 复位设备，释放串口。
2. 重新调用 `repl_exec`，通常即可恢复。
3. 若仍失败，重复一次 soft_reset → repl_exec；本流程中第 4/6/11 轮失败后均通过此方式恢复。
4. 连续多次失败再考虑检查接线或重新插拔 USB。

> 来源：20260718_074004_按下key1-只有G05小灯亮-1s后-G05灭 任务提取，已经用户确认
