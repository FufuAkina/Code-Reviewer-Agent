from harness.tools.list_files import ListFilesTool


def test_list_files():
    tool = ListFilesTool()

    print("测试 1：列出当前目录")
    result = tool.execute(directory=".")
    print(f"成功: {result.success}")
    print(f"结果:\n{result.data}\n")

    print("=" * 60)

    print("测试 2：列出 Python 文件")
    result = tool.execute(directory=".", pattern="*.py")
    print(f"成功: {result.success}")
    print(f"文件数: {result.metadata.get('file_count', 0)}")
    print(f"结果:\n{result.data}\n")

    print("=" * 60)

    print("测试 3：不存在的目录")
    result = tool.execute(directory="nonexistent")
    print(f"成功: {result.success}")
    print(f"错误: {result.error}")


if __name__ == "__main__":
    test_list_files()
