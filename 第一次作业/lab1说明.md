# 学生宿舍管理系统程序说明

## 一、任务分析

本程实现了一个简单的学生宿舍管理系统，能够完成以下功能：

1. 按学号查询学生信息
2. 录入新的学生信息（并进行有效性校验）
3. 显示所有学生信息
4. 退出系统
   
--- 

## 二、思路构建

1. **数据结构设计**：
   - 使用列表`students`存储所有学生信息，每个学生用一个字典表示，包含学号、姓名、性别、宿舍房间号、联系电话等字段。

2. **功能模块划分**：
   - `search_student()`：按学号查找学生
   - `add_student()`：录入新学生，并对输入进行校验
   - `show_all_students()`：显示所有学生信息
   - `main()`：主菜单循环，负责用户交互和功能调度

3. **输入校验**：
   - 学号必须为数字且唯一
   - 姓名不能为空
   - 性别只能为“男”或“女”
   - 宿舍房间号不能为空
   - 联系电话必须为11位数字

---

## 三、代码解释

### 1. 数据初始化
```python
students = [
    {"学号": "1", "姓名": "小A", "性别": "男", "宿舍房间号": "101", "联系电话": "10000000001"},
    ...
]
```
- 用于存储初始的学生信息。

### 2. 按学号查找学生
```python
def search_student():
    sid = input("请输入要查询的学号: ").strip()
    for stu in students:
        if stu["学号"] == sid:
            ... # 打印学生信息
            return
    print("未找到该学号对应的学生信息。")
```
- 遍历学生列表，查找学号匹配的学生。

### 3. 录入新学生（含校验）
```python
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
    ... # 依次校验姓名、性别、房间号、电话
    student = { ... }
    students.append(student)
    print("学生信息录入成功！")
```
- 通过循环和条件判断，确保每项输入都合法。

### 4. 显示所有学生信息
```python
def show_all_students():
    if not students:
        print("当前没有学生信息。")
        return
    for idx, stu in enumerate(students, start=1):
        ... # 打印每位学生信息
```
- 依次输出所有学生的详细信息。

### 5. 主菜单与程序入口
```python
def main():
    while True:
        print("学生宿舍管理系统")
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

if __name__ == "__main__":
    main()
```
- 实现循环菜单，用户可多次操作，直至选择退出。

---

## 四、总结

本程序结构清晰，功能模块化，适合初学者理解和扩展。通过输入校验保证了数据的有效性和系统的健壮性。
