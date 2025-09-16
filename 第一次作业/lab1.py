# 初始学生信息
students = [
    {"学号": "1", "姓名": "小A", "性别": "男", "宿舍房间号": "101", "联系电话": "10000000001"},
    {"学号": "2", "姓名": "小B", "性别": "女", "宿舍房间号": "102", "联系电话": "10000000002"},
    {"学号": "3", "姓名": "小C", "性别": "男", "宿舍房间号": "103", "联系电话": "10000000003"},
    {"学号": "4", "姓名": "小D", "性别": "女", "宿舍房间号": "104", "联系电话": "10000000004"},
    {"学号": "5", "姓名": "小E", "性别": "男", "宿舍房间号": "105", "联系电话": "10000000005"}
]

# 功能1：按学号查找
def search_student():
    sid = input("请输入要查询的学号: ").strip()
    for stu in students:
        if stu["学号"] == sid:
            print("\n找到学生信息：")
            for k, v in stu.items():
                print(f"{k}: {v}")
            return
    print("未找到该学号对应的学生信息。")

# 功能2：录入新学生
def add_student():
    while True:
        sid = input("请输入学号: ").strip()
        if not sid.isdigit():
            print("学号必须为数字，请重新输入。")
            continue
        if any(stu["学号"] == sid for stu in students):
            print("学号已存在，请重新输入。")
            continue
        break
    while True:
        name = input("请输入姓名： ").strip()
        if not name:
            print("姓名不能为空，请重新输入。")
            continue
        break
    while True:
        gender = input("请输入性别(男/女): ").strip()
        if gender not in ("男", "女"):
            print("性别只能为'男'或'女'，请重新输入。")
            continue
        break
    while True:
        room = input("请输入宿舍房间号: ").strip()
        if not room:
            print("宿舍房间号不能为空，请重新输入。")
            continue
        break
    while True:
        phone = input("请输入联系电话: ").strip()
        if not (phone.isdigit() and len(phone) == 11):
            print("联系电话必须为11位数字，请重新输入。")
            continue
        break
    student = {
        "学号": sid,
        "姓名": name,
        "性别": gender,
        "宿舍房间号": room,
        "联系电话": phone
    }
    students.append(student)
    print("学生信息录入成功！")

# 功能3：显示所有学生
def show_all_students():
    if not students:
        print("当前没有学生信息。")
        return
    print("\n所有学生信息如下：")
    for idx, stu in enumerate(students, start=1):
        print(f"第{idx}位学生:")
        for k, v in stu.items():
            print(f"  {k}: {v}")
        print("-" * 30)

# 系统主菜单
def main():
    while True:
        print("学生宿舍管理系统")
        print("1. 按学号查询学生信息")
        print("2. 录入新的学生信息")
        print("3. 显示所有学生信息")
        print("4. 退出系统")
        choice = input("请选择功能(1-4): ").strip()
        
        if choice == "1":
            search_student()
        elif choice == "2":
            add_student()
        elif choice == "3":
            show_all_students()
        elif choice == "4":
            print("退出系统，感谢使用！")
            break
        else:
            print("输入错误，请重新选择。")

# 程序入口
if __name__ == "__main__":
    main()
