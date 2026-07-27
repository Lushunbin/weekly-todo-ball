# Weekly Todo Ball

一款无需登录、无需联网的 Windows 单机版每周待办工具。它将本周任务保存在本地 SQLite 数据库中，并可最小化为可拖动的桌面悬浮球。

## 快速开始

下载并双击 [dist/WeeklyTodo.exe](dist/WeeklyTodo.exe) 即可使用，无需安装 Python 或其他运行环境。

首次运行会自动在当前 Windows 用户的本地目录创建数据库：

```text
%LOCALAPPDATA%\WeeklyTodoBall\todo.db
```

所有待办只保存在本机，不会上传到云端，也不需要账号。

## 功能

- 按周管理待办：前后切换周，或通过日历选择任意日期并跳转到所在周。
- 圆形勾选：点击待办前的圆圈即可标记完成，再次点击可恢复未完成。
- 待办编辑：支持添加、修改和删除当前周待办。
- 历史查询：按日期或待办内容搜索历史周记录。
- 单周导出：将当前周待办导出为 UTF-8 文本，每项按 `1. 2. 3.` 编号。
- 悬浮球：编辑窗口最小化后变成悬浮球；可拖动，单击展开、双击返回完整编辑界面。
- 自适应展开：面板根据悬浮球所在位置向屏幕内侧展开，项目过多时可滚动查看。

## 使用说明

1. 在顶部输入框填写待办，点击“添加”或按 Enter。
2. 点击顶部日期文字或“日历”，选择任意一天即可切换到该日所属周。
3. 点击标题栏最小化按钮，窗口会缩为悬浮球；按住悬浮球可以移动位置。
4. 单击悬浮球查看本周任务，双击悬浮球回到完整编辑窗口。
5. 点击“导出本周”选择保存位置，即可生成编号待办清单。

## 仓库文件

| 路径 | 说明 |
| --- | --- |
| `dist/WeeklyTodo.exe` | 已打包的 Windows 单文件程序。 |
| `weekly_todo.py` | 应用源码，使用 Python 标准库 Tkinter 与 SQLite。 |
| `data/todo.db` | 空的 SQLite 数据库模板，不含任何个人待办。 |

## 开发与打包

开发运行需要 Python 3.10 或更新版本（包含 Tkinter）：

```powershell
python weekly_todo.py
```

使用 PyInstaller 重新打包：

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name WeeklyTodo weekly_todo.py
```

## 隐私与数据

仓库中提交的 `data/todo.db` 是新建的空数据库，仅用于说明数据格式。程序实际使用当前 Windows 用户目录中的数据库；更新程序或从本仓库下载新版 exe 不会清空现有待办。

## License

MIT
