import sys
import pandas as pd
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import (QFileDialog, QMessageBox, QLabel, QTableWidget,
                             QTableWidgetItem, QComboBox, QCompleter, QLineEdit,
                             QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QInputDialog)
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import Qt, pyqtSignal
import sqlite3
import matplotlib.pyplot as plt
from collections import defaultdict
import matplotlib.font_manager as fm

class ScheduleManager(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_connection = self.connect_to_database()
        self.imported_file_path = None
        self.student_list = []  # 添加学生列表属性
        self.course_list = []   # 添加课程列表属性
        self.initUI()
        self.load_courses()
        self.update_dropdowns()  # 初始化时更新下拉列表
        self.time_slots = ["上午一段", "上午二段", "下午一段", "下午二段", "晚修"]
        self.weekdays = ["周一", "周二", "周三", "周四", "周五", "周六"]  # 添加星期几列表

    def initUI(self):
        self.setWindowTitle("学生课表管理程序")
        self.setGeometry(100, 100, 1100, 670) 

        # Status Label
        self.status_label = QLabel("等待导入表格中（如不导入数据则无法导出为 Excel 表格）", self)
        self.status_label.setGeometry(50, 10, 1000, 30)
        self.status_label.setStyleSheet("color: gray;")

        # Table Widget
        self.table_widget = QTableWidget(self)
        self.table_widget.setGeometry(50, 50, 1000, 400)
        self.table_widget.setColumnCount(8)
        self.table_widget.setHorizontalHeaderLabels(['学生姓名', '班级', '课程名称', '学分', '星期', '行课时间', '周数', '教室'])
    
        # 调整列宽
        self.table_widget.setColumnWidth(0, 100)  # 学生姓名列
        self.table_widget.setColumnWidth(1, 160)  # 班级列
        self.table_widget.setColumnWidth(2, 200)  # 课程名称列
        self.table_widget.setColumnWidth(3, 40)   # 学分列
        self.table_widget.setColumnWidth(4, 60)   # 星期列
        self.table_widget.setColumnWidth(5, 120)  # 行课时间列
        self.table_widget.setColumnWidth(6, 40)  # 周数列
        self.table_widget.setColumnWidth(7, 100)  # 教室列

        
        self.table_widget.verticalHeader().sectionClicked.connect(self.delete_row)

        # Original Buttons
        self.import_btn = QtWidgets.QPushButton("导入课程信息", self)
        self.import_btn.setGeometry(50, 470, 200, 40)
        self.import_btn.clicked.connect(self.import_schedule)

        self.init_btn = QtWidgets.QPushButton("初始化学生与课程信息", self)
        self.init_btn.setGeometry(260, 470, 200, 40)
        self.init_btn.clicked.connect(self.initialize_data)

        self.export_sqlite_btn = QtWidgets.QPushButton("导出至SQLite", self)
        self.export_sqlite_btn.setGeometry(470, 470, 200, 40)
        self.export_sqlite_btn.clicked.connect(self.export_to_sqlite)

        self.import_sqlite_btn = QtWidgets.QPushButton("从SQLite导入", self)
        self.import_sqlite_btn.setGeometry(680, 470, 200, 40)
        self.import_sqlite_btn.clicked.connect(self.import_from_sqlite)

        self.import_sqlite_btn = QtWidgets.QPushButton("导入学生数据", self)
        self.import_sqlite_btn.setGeometry(890, 470, 160, 40)
        self.import_sqlite_btn.clicked.connect(self.import_from_sqlite)

        self.import_sqlite_btn = QtWidgets.QPushButton("导入课程数据", self)
        self.import_sqlite_btn.setGeometry(890, 520, 160, 40)
        self.import_sqlite_btn.clicked.connect(self.import_from_sqlite)

        self.import_sqlite_btn = QtWidgets.QPushButton("导出为Excel表格", self)
        self.import_sqlite_btn.setGeometry(890, 570, 160, 40)
        self.import_sqlite_btn.clicked.connect(self.export_to_excel)

        self.add_row_btn = QtWidgets.QPushButton("添加新行", self)
        self.add_row_btn.setGeometry(50, 520, 200, 40)
        self.add_row_btn.clicked.connect(self.add_new_row)

        # New Buttons for Management
        self.manage_students_btn = QtWidgets.QPushButton("学生管理", self)
        self.manage_students_btn.setGeometry(260, 520, 200, 40)
        self.manage_students_btn.clicked.connect(self.show_student_manager)

        self.manage_courses_btn = QtWidgets.QPushButton("课程管理", self)
        self.manage_courses_btn.setGeometry(470, 520, 200, 40)
        self.manage_courses_btn.clicked.connect(self.show_course_manager)

        self.auto_schedule_btn = QtWidgets.QPushButton("自动排课", self)
        self.auto_schedule_btn.setGeometry(680, 570, 200, 40)
        self.auto_schedule_btn.clicked.connect(self.auto_schedule)

        self.update_data_btn = QtWidgets.QPushButton("更新学生课程数据", self)
        self.update_data_btn.setGeometry(680, 520, 200, 40)
        self.update_data_btn.clicked.connect(self.update_student_course_data)

        self.class_label = QLabel("选择班级:", self)
        self.class_label.setGeometry(50, 620, 100, 30)
        self.class_combobox = QComboBox(self)
        self.class_combobox.setGeometry(150, 620, 200, 30)
        self.load_class_combobox()

        self.week_label = QLabel("选择周数:", self)
        self.week_label.setGeometry(370, 620, 100, 30)
        self.week_combobox = QComboBox(self)
        self.week_combobox.setGeometry(470, 620, 200, 30)
        self.load_week_combobox()

        self.student_label = QLabel("选择学生:", self)
        self.student_label.setGeometry(690, 620, 100, 30)
        self.student_combobox = QComboBox(self)
        self.student_combobox.setGeometry(790, 620, 200, 30)
        self.load_student_combobox()

        self.plot_btn = QtWidgets.QPushButton("统计上课频次", self)
        self.plot_btn.setGeometry(50, 570, 200, 40)
        self.plot_btn.clicked.connect(self.plot_class_frequency)

        self.export_student_btn = QtWidgets.QPushButton("导出学生课程安排", self)
        self.export_student_btn.setGeometry(260, 570, 200, 40)
        self.export_student_btn.clicked.connect(self.export_student_schedule)

        self.export_class_btn = QtWidgets.QPushButton("导出班级统计信息", self)
        self.export_class_btn.setGeometry(470, 570, 200, 40)
        self.export_class_btn.clicked.connect(self.export_class_statistics)

    def count_classes_per_weekday(self):
        selected_class = self.class_combobox.currentText()
        selected_week = self.week_combobox.currentText().replace("第", "").replace("周", "")
        
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT s.weekday, COUNT(*) 
            FROM schedule s
            JOIN students st ON s.student_name = st.student_name
            JOIN courses c ON s.course_name = c.course_name
            WHERE st.class_name = ? AND ? BETWEEN CAST(SUBSTR(c.semester, 1, INSTR(c.semester, '-') - 1) AS INTEGER)
            AND CAST(SUBSTR(c.semester, INSTR(c.semester, '-') + 1) AS INTEGER)
            GROUP BY s.weekday
        """, (selected_class, selected_week))
        rows = cursor.fetchall()

        # 定义每周的天数（不包括星期天）
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六"]
        class_count = {day: 0 for day in weekdays}

        # 统计上课频次
        for weekday, count in rows:
            if weekday in class_count:
                class_count[weekday] = count

        return class_count, weekdays

    def plot_class_frequency(self):
        class_count, weekdays = self.count_classes_per_weekday()

        # 生成数据
        frequencies = [class_count[day] for day in weekdays]

        font_path = './ubuntu.ttf'
        font_prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.sans-serif'] = [font_path]
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams.update({'font.size': 14})

        # 绘制柱状图
        plt.figure(figsize=(12, 8))
        plt.bar(weekdays, frequencies, color='skyblue')
        plt.xlabel('星期', fontsize=16, fontproperties=font_prop)
        plt.ylabel('上课频次', fontsize=16, fontproperties=font_prop)
        plt.title('每周每天上课频次统计', fontsize=20, fontproperties=font_prop)
        plt.xticks(fontsize=14, fontproperties=font_prop)
        plt.yticks(fontsize=14, fontproperties=font_prop)
        plt.show()

    def load_class_combobox(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT DISTINCT class_name FROM students")
        classes = [row[0] for row in cursor.fetchall()]
        self.class_combobox.addItems(classes)

    def load_week_combobox(self):
        weeks = [f"第{week}周" for week in range(1, 18)]
        self.week_combobox.addItems(weeks)

    def load_student_combobox(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT student_name FROM students")
        students = [row[0] for row in cursor.fetchall()]
        self.student_combobox.addItems(students)

    def export_student_schedule(self):
        selected_student = self.student_combobox.currentText()
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT * FROM schedule WHERE student_name = ?", (selected_student,))
        rows = cursor.fetchall()

        if not rows:
            QMessageBox.information(self, "提示", "没有找到该学生的课程安排")
            return

        data = {
            '学生姓名': [],
            '课程名称': [],
            '学分': [],
            '星期': [],
            '行课时间': [],
            '教室': []
        }

        for row in rows:
            data['学生姓名'].append(row[1])
            data['课程名称'].append(row[2])
            data['学分'].append(row[3])
            data['星期'].append(row[4])
            data['行课时间'].append(row[5])
            data['教室'].append(row[6])

        df = pd.DataFrame(data)
        file_name, _ = QFileDialog.getSaveFileName(self, "导出课程安排", "", "Excel Files (*.xlsx);;All Files (*)")
        
        if file_name:
            if not file_name.endswith('.xlsx'):
                file_name += '.xlsx'
            df.to_excel(file_name, index=False)
            QMessageBox.information(self, "成功", "课程安排已成功导出")

    def export_class_statistics(self):
        selected_class = self.class_combobox.currentText()
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT s.student_name, s.course_name, s.credit, s.weekday, s.time_slot, s.classroom
            FROM schedule s
            JOIN students st ON s.student_name = st.student_name
            WHERE st.class_name = ?
        """, (selected_class,))
        rows = cursor.fetchall()

        if not rows:
            QMessageBox.information(self, "提示", "没有找到该班级的统计信息")
            return

        data = {
            '学生姓名': [],
            '课程名称': [],
            '学分': [],
            '星期': [],
            '行课时间': [],
            '教室': []
        }

        for row in rows:
            data['学生姓名'].append(row[0])
            data['课程名称'].append(row[1])
            data['学分'].append(row[2])
            data['星期'].append(row[3])
            data['行课时间'].append(row[4])
            data['教室'].append(row[5])

        df = pd.DataFrame(data)
        file_name, _ = QFileDialog.getSaveFileName(self, "导出统计信息", "", "Excel Files (*.xlsx);;All Files (*)")
        
        if file_name:
            if not file_name.endswith('.xlsx'):
                file_name += '.xlsx'
            df.to_excel(file_name, index=False)
            QMessageBox.information(self, "成功", "班级统计信息已成功导出")

    def auto_schedule(self):
        """自动排课"""
        try:
            print("开始自动排课...")
            cursor = self.db_connection.cursor()
            
            # 检查数据库连接
            if not self.db_connection:
                raise Exception("数据库连接失败")
            
            # 获取学生列表
            try:
                cursor.execute("SELECT student_name FROM students")
                students = [row[0] for row in cursor.fetchall()]
                print(f"获取到 {len(students)} 名学生")
            except Exception as e:
                raise Exception(f"获取学生列表失败: {str(e)}")

            # 获取课程列表
            try:
                cursor.execute("SELECT course_name, credit FROM courses")
                courses = cursor.fetchall()
                print(f"获取到 {len(courses)} 门课程")
            except Exception as e:
                raise Exception(f"获取课程列表失败: {str(e)}")

            # 检查数据是否足够
            if not students:
                raise Exception("没有找到学生信息")
            if not courses:
                raise Exception("没有找到课程信息")

            print("清空现有课表...")
            try:
                # 清空现有课表
                cursor.execute("DELETE FROM schedule")
            except Exception as e:
                raise Exception(f"清空课表失败: {str(e)}")
            
            # 准备插入的数据
            print("生成排课数据...")
            schedule = []
            try:
                import random
                building_numbers = [1, 2, 4]  # 可选的教学楼号
                
                for student in students:
                    for course_name, credit in courses:
                        weekday = self.weekdays[len(schedule) % len(self.weekdays)]
                        time_slot = self.time_slots[len(schedule) % len(self.time_slots)]
                        
                        # 生成四位教室号：H + 教学楼号(1/2/4) + 两位房间号(01-20)
                        building = random.choice(building_numbers)
                        room_number = f"H{building}{random.randint(1, 20):02d}"

                        schedule.append((
                            student,
                            course_name,
                            credit,
                            weekday,
                            time_slot,
                            room_number
                        ))
                print(f"生成了 {len(schedule)} 条排课记录")
            except Exception as e:
                raise Exception(f"生成排课数据失败: {str(e)}")


            # 批量插入数据
            print("插入排课数据到数据库...")
            try:
                cursor.executemany("""
                    INSERT INTO schedule 
                    (student_name, course_name, credit, weekday, time_slot, classroom)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, schedule)
                
                self.db_connection.commit()
                print("数据库提交成功")
            except Exception as e:
                self.db_connection.rollback()
                raise Exception(f"插入数据失败: {str(e)}")

            # 刷新表格显示
            print("更新表格显示...")
            try:
                self.load_schedule_into_table()
            except Exception as e:
                raise Exception(f"更新表格显示失败: {str(e)}")

            print("自动排课完成")
            QMessageBox.information(self, "成功", "自动排课成功")
            
        except Exception as e:
            error_msg = f"自动排课失败: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            # 打印详细的错误堆栈
            import traceback
            traceback.print_exc()

    def show_student_manager(self):
        """显示学生管理窗口"""
        self.student_manager = StudentManager(self.db_connection, self)
        self.student_manager.reload_students_signal.connect(self.load_students)
        self.student_manager.show()

    def show_course_manager(self):
        """显示课程管理窗口"""
        self.course_manager = CourseManager(self.db_connection, self)
        self.course_manager.reload_courses_signal.connect(self.load_courses)
        self.course_manager.show()

    def initialize_data(self):
        """初始化学生与课程信息或导出课表"""
        try:
            cursor = self.db_connection.cursor()
            
            # 清空现有数据
            cursor.execute("DELETE FROM schedule")
            cursor.execute("DELETE FROM students")
            cursor.execute("DELETE FROM courses")
            
            # 重置自增ID
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('students', 'courses', 'schedule')")
            
            # 初始化默认学生 - 移除多余的空格
            default_students = [
                ('林悦溪', '自动化211'), ('苏逸晨', '自动化211'), ('林宇轩', '自动化212'),
                ('叶梓豪', '自动化213'), ('苏锦瑶', '自动化212'), ('沈俊辉', '自动化221'),
                ('秦泽凯', '自动化222'), ('许皓阳', '自动化223'), ('叶婉清', '自动化213'),
                ('唐文昊', '自动化231'), ('白睿渊', '自动化232'), ('楚晨峰', '自动化233'),
                ('沈梦璃', '自动化221'), ('柳靖琪', '自动化234'), ('赵景铄', '自动化211'),
                ('陈俊驰', '自动化212'), ('秦诗涵', '自动化222'), ('周远航', '自动化213'),
                ('陆博超', '自动化221'), ('郑子轩', '自动化222'), ('许静雅', '自动化223'),
                ('何宇澄', '自动化223'), ('冯睿晨', '自动化231'), ('罗嘉豪', '自动化232'),
                ('唐晓萱', '自动化231'), ('萧启铭', '自动化233'), ('田耀辉', '自动化234'),
                ('孙逸飞', '自动化211'), ('白若冰', '自动化232'), ('钱锦程', '自动化212'),
                ('吴梓轩', '自动化213'), ('梁梓铭', '自动化221'), ('楚依琳', '自动化233'),
                ('谢翰飞', '自动化222'), ('傅晨熙', '自动化223'), ('彭俊楠', '自动化231'),
                ('柳雨薇', '自动化234'), ('蒋睿峰', '自动化232'), ('韩浩宇', '自动化233'),
                ('曹宇翔', '自动化234'), ('赵灵芸', '自动化211'), ('陈佳凝', '自动化212'),
                ('周语蝶', '自动化213'), ('陆芷晴', '自动化221'), ('郑雅琪', '自动化222'),
                ('何思瑶', '自动化223'), ('田雨昕', '自动化234'), ('钱浅兮', '自动化212'),
                ('谢诗韵', '自动化222'), ('傅冰清', '自动化223'), ('彭晓兰', '自动化231'),
                ('蒋雨桐', '自动化232'), ('韩紫菱', '自动化233'), ('曹静婉', '自动化234')
            ]
            
            # 使用参数化查询插入数据
            cursor.executemany("""
                INSERT INTO students (student_name, class_name)
                VALUES (?, ?)
            """, [(name.strip(), class_name.strip()) for name, class_name in default_students])
            
            # 初始化默认课程
            default_courses = [
                ('高等数学', 4.0, '3-16'),
                ('线性代数', 3.0, '3-14'),
                ('大学物理', 4.0, '6-15'),
                ('Python编程技术', 2.5, '3-16'),
                ('思想道德与法治', 3.5, '9-14')
            ]
            
            cursor.executemany("""
                INSERT INTO courses (course_name, credit, semester)
                VALUES (?, ?, ?)
            """, [(name.strip(), credit, semester.strip()) for name, credit, semester in default_courses])
            
            self.db_connection.commit()
            
            # 清空并重新加载表格
            self.table_widget.setRowCount(0)
            self.load_courses()
            
            QMessageBox.information(self, "成功", "学生与课程信息已初始化")
            
        except Exception as e:
            self.db_connection.rollback()
            QMessageBox.critical(self, "错误", f"初始化失败: {str(e)}")
            return

    def update_student_course_data(self):
        """更新学生和课程数据，并更新选择学生下拉菜单"""
        # 获取最新的学生和课程列表
        cursor = self.db_connection.cursor()
        
        # 更新学生列表
        cursor.execute("SELECT student_name FROM students")
        self.student_list = [row[0] for row in cursor.fetchall()]
        
        # 更新课程列表
        cursor.execute("SELECT course_name FROM courses")
        self.course_list = [row[0] for row in cursor.fetchall()]
        
        # 更新选择学生的下拉菜单
        self.student_combobox.clear()
        self.student_combobox.addItems(self.student_list)
        
        # 只更新现有行的下拉菜单选项，不改变已选择的值
        for row in range(self.table_widget.rowCount()):
            # 更新学生下拉菜单（第0列）
            student_widget = self.table_widget.cellWidget(row, 0)
            if isinstance(student_widget, QComboBox):
                current_student = student_widget.currentText()
                student_widget.clear()
                student_widget.addItems(self.student_list)
                student_widget.setCurrentText(current_student)
            
            # 更新课程下拉菜单（第2列）
            course_widget = self.table_widget.cellWidget(row, 2)
            if isinstance(course_widget, QComboBox):
                current_course = course_widget.currentText()
                course_widget.clear()
                course_widget.addItems(self.course_list)
                course_widget.setCurrentText(current_course)
        
        QMessageBox.information(self, "成功", "下拉菜单选项已更新")
    
    def export_to_excel(self):
        """导出课表到Excel文件"""
        try:
            # 收集表格数据
            data = {
                '学生姓名': [],
                '班级': [],
                '课程名称': [],
                '学分': [],
                '星期': [],
                '行课时间': [],
                '周数': [],
                '教室': []
            }
            
            # 从表格中获取数据
            for row in range(self.table_widget.rowCount()):
                # 获取各列的数据，根据控件类型使用不同的方法获取值
                student_widget = self.table_widget.cellWidget(row, 0)
                class_widget = self.table_widget.cellWidget(row, 1)
                course_widget = self.table_widget.cellWidget(row, 2)
                credit_widget = self.table_widget.cellWidget(row, 3)
                weekday_widget = self.table_widget.cellWidget(row, 4)
                time_widget = self.table_widget.cellWidget(row, 5)
                semester_widget = self.table_widget.cellWidget(row, 6)
                classroom_widget = self.table_widget.cellWidget(row, 7)

                # 根据控件类型获取值
                data['学生姓名'].append(student_widget.currentText() if isinstance(student_widget, QComboBox) else "")
                data['班级'].append(class_widget.text() if isinstance(class_widget, QLineEdit) else "")
                data['课程名称'].append(course_widget.currentText() if isinstance(course_widget, QComboBox) else "")
                data['学分'].append(credit_widget.text() if isinstance(credit_widget, QLineEdit) else "")
                data['星期'].append(weekday_widget.currentText() if isinstance(weekday_widget, QComboBox) else "")
                data['行课时间'].append(time_widget.currentText() if isinstance(time_widget, QComboBox) else "")
                data['周数'].append(semester_widget.text() if isinstance(semester_widget, QLineEdit) else "")
                data['教室'].append(classroom_widget.text() if isinstance(classroom_widget, QLineEdit) else "")
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 选择保存位置
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "导出课表",
                "",
                "Excel Files (*.xlsx);;All Files (*)",
                options=options
            )
            
            if file_name:
                # 如果文件名没有.xlsx后缀，添加它
                if not file_name.endswith('.xlsx'):
                    file_name += '.xlsx'
                
                # 导出到Excel
                df.to_excel(file_name, index=False)
                QMessageBox.information(self, "成功", "课表已成功导出")
                
        except Exception as e:
            error_msg = f"导出失败: {str(e)}"
            print(error_msg)  # 打印错误信息到控制台
            QMessageBox.critical(self, "错误", error_msg)
            # 打印详细的错误堆栈
            import traceback
            traceback.print_exc()

    def connect_to_database(self):
        """初始化数据库连接并创建必要的表"""
        try:
            conn = sqlite3.connect("schedule.db")
            cursor = conn.cursor()

            # 先删除旧表以确保表结构更新
            cursor.execute("DROP TABLE IF EXISTS schedule")
            
            # 创建新的课程表，确保包含所有必要的列
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT,
                    course_name TEXT,
                    credit REAL,
                    weekday TEXT,
                    time_slot TEXT,
                    classroom TEXT,
                    semester TEXT
                )
            """)
            
            # 创建或更新学生表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT UNIQUE,
                    class_name TEXT
                )
            """)
            
            # 创建或更新课程表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_name TEXT UNIQUE,
                    credit REAL,
                    semester TEXT
                )
            """)
            
            conn.commit()
            return conn
        except sqlite3.Error as err:
            QMessageBox.critical(self, "数据库错误", str(err))
            sys.exit()

    def load_students(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT student_name FROM students")
        self.student_list = [row[0] for row in cursor.fetchall()]
        self.update_comboboxes()

    def load_courses(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT course_name FROM courses")
        self.course_list = [row[0] for row in cursor.fetchall()]
        self.update_comboboxes()

    def update_comboboxes(self):
        for row in range(self.table_widget.rowCount()):
            student_combo = self.create_student_combobox(self.table_widget.item(row, 0).text() if self.table_widget.item(row, 0) else "")
            self.table_widget.setCellWidget(row, 0, student_combo)
            course_combo = self.create_course_combobox(self.table_widget.item(row, 1).text() if self.table_widget.item(row, 1) else "")
            self.table_widget.setCellWidget(row, 1, course_combo)

    def import_schedule(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "选择 Excel 文件", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_name:
            try:
                df = pd.read_excel(file_name, dtype=str)  # Ensure all data is read as strings

                cursor = self.db_connection.cursor()
                cursor.execute("DELETE FROM schedule")
                self.db_connection.commit()

                for index, row in df.iterrows():
                    student_name = row['学生姓名']
                    course_name = row['课程名称']
                    credit = int(row['学分'])  # Ensure credit is an integer
                    time_slot = row['行课时间']
                    classroom = f"H{row['教室']}"  # Add 'H' prefix

                    cursor.execute("""
                        INSERT INTO schedule (student_name, course_name, credit, time_slot, classroom)
                        VALUES (?, ?, ?, ?, ?)
                    """, (student_name, course_name, credit, time_slot, classroom))
                
                self.db_connection.commit()
                self.imported_file_path = file_name
                self.update_status_label("excel")
                self.load_schedule_into_table()
                QMessageBox.information(self, "成功", "课程信息导入成功")
            except Exception as e:
                print(f"导入失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def update_status_label(self, source):
        if source == "excel":
            self.status_label.setText(f"已导入: {self.imported_file_path}")
            self.status_label.setStyleSheet("color: green;")
        elif source == "sqlite":
            self.status_label.setText("已从SQLite数据库导入")
            self.status_label.setStyleSheet("color: blue;")
        elif source == "initialized":
            self.status_label.setText("数据已初始化")
            self.status_label.setStyleSheet("color: blue;")
        else:
            self.status_label.setText("等待导入表格中")
            self.status_label.setStyleSheet("color: gray;")

    def load_schedule_into_table(self):
        self.table_widget.setRowCount(0)

        cursor = self.db_connection.cursor()
        # 修改 SQL 查询，移除注释
        cursor.execute("""
            SELECT 
                s.student_name, 
                st.class_name, 
                s.course_name, 
                c.credit, 
                s.weekday, 
                s.time_slot, 
                c.semester, 
                s.classroom
            FROM schedule s
            LEFT JOIN students st ON s.student_name = st.student_name
            LEFT JOIN courses c ON s.course_name = c.course_name
        """)
        rows = cursor.fetchall()

        for row_data in rows:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)
            
            for column, data in enumerate(row_data):
                if isinstance(data, bytes):
                    data = data.decode('utf-8')

                if column == 0:  # 学生姓名
                    combo = self.create_student_combobox(str(data))
                    self.table_widget.setCellWidget(row_position, column, combo)
                elif column == 1:  # 班级
                    line_edit = QLineEdit(str(data))
                    line_edit.setReadOnly(True)
                    self.table_widget.setCellWidget(row_position, column, line_edit)
                elif column == 2:  # 课程名称
                    combo = self.create_course_combobox(str(data))
                    self.table_widget.setCellWidget(row_position, column, combo)
                elif column == 3:  # 学分
                    line_edit = QLineEdit(str(data))
                    line_edit.setReadOnly(True)
                    self.table_widget.setCellWidget(row_position, column, line_edit)
                elif column == 4:  # 星期
                    combo = self.create_weekday_combobox(str(data))
                    self.table_widget.setCellWidget(row_position, column, combo)
                elif column == 5:  # 时间段
                    combo = self.create_time_slot_combobox(str(data))
                    self.table_widget.setCellWidget(row_position, column, combo)
                elif column == 6:  # 周数
                    line_edit = QLineEdit(str(data))
                    line_edit.setReadOnly(True)
                    self.table_widget.setCellWidget(row_position, column, line_edit)
                elif column == 7:  # 教室列
                    line_edit = QLineEdit(str(data))
                    # 创建自定义的验证器，允许后缀
                    validator = QtGui.QRegExpValidator(QtCore.QRegExp(r"H?[124]\d{2}[1-9]"))
                    line_edit.setValidator(validator)
                    line_edit.editingFinished.connect(lambda le=line_edit: self.add_classroom_prefix(le))
                    self.table_widget.setCellWidget(row_position, column, line_edit)

    def update_student_class(self, student_name, combo):
        """更新学生班级信息"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT class_name FROM students WHERE student_name = ?", (student_name,))
            result = cursor.fetchone()
            
            if result:
                row = self.table_widget.indexAt(combo.pos()).row()
                class_edit = self.table_widget.cellWidget(row, 1)  # 班级列
                if class_edit and isinstance(class_edit, QLineEdit):
                    class_edit.setText(result[0])
        except Exception as e:
            print(f"更新班级信息失败: {str(e)}")

    def update_course_info(self, course_name, combo):
        """更新课程学分和周数信息"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT credit, semester FROM courses WHERE course_name = ?", (course_name,))
            result = cursor.fetchone()
            
            if result:
                row = self.table_widget.indexAt(combo.pos()).row()
                credit_edit = self.table_widget.cellWidget(row, 3)  # 学分列
                semester_edit = self.table_widget.cellWidget(row, 6)  # 周数列
                
                if credit_edit and isinstance(credit_edit, QLineEdit):
                    credit_edit.setText(str(result[0]))
                if semester_edit and isinstance(semester_edit, QLineEdit):
                    semester_edit.setText(str(result[1]))
        except Exception as e:
            print(f"更新课程信息失败: {str(e)}")


    def create_course_combobox(self, current_text=""):
        """创建课程下拉框"""
        combo = QComboBox()
        combo.addItems(self.course_list)
        combo.setEditable(True)
        combo.setCurrentText(current_text)

        completer = QCompleter(self.course_list, combo)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combo.setCompleter(completer)

        # 添加信号连接
        combo.currentTextChanged.connect(lambda text, c=combo: self.update_course_info(text, c))

        return combo

    def create_time_slot_combobox(self, current_text=""):
        combo = QComboBox()
        combo.addItems(self.time_slots)
        combo.setEditable(True)
        combo.setCurrentText(current_text)

        completer = QCompleter(self.time_slots, combo)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combo.setCompleter(completer)

        return combo
    
    def create_weekday_combobox(self, current_text=""):
        """创建星期下拉框"""
        combo = QComboBox()
        combo.addItems(self.weekdays)
        combo.setCurrentText(current_text)
        return combo

    def add_classroom_prefix(self, line_edit):
        text = line_edit.text()
        if not text.startswith('H'):
            line_edit.setText(f'H{text}')

    def add_new_row(self):
        """添加新行"""
        row_position = self.table_widget.rowCount()
        self.table_widget.insertRow(row_position)

        for column in range(self.table_widget.columnCount()):
            if column == 0:  # 学生姓名列
                combo = self.create_student_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 1:  # 班级列 - 只读文本框
                line_edit = QLineEdit()
                line_edit.setReadOnly(True)
                self.table_widget.setCellWidget(row_position, column, line_edit)
            elif column == 2:  # 课程名称列
                combo = self.create_course_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 3:  # 学分列
                line_edit = QLineEdit()
                line_edit.setReadOnly(True)
                self.table_widget.setCellWidget(row_position, column, line_edit)
            elif column == 4:  # 星期列
                combo = self.create_weekday_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 5:  # 时间段列
                combo = self.create_time_slot_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 6:  # 周数列
                line_edit = QLineEdit()
                line_edit.setReadOnly(True)
                self.table_widget.setCellWidget(row_position, column, line_edit)
            elif column == 7:  # 教室列
                line_edit = QLineEdit()
                validator = QtGui.QRegExpValidator(QtCore.QRegExp(r"H?[124]\d{2}[1-9]"))
                line_edit.setValidator(validator)
                line_edit.editingFinished.connect(lambda le=line_edit: self.add_classroom_prefix(le))
                self.table_widget.setCellWidget(row_position, column, line_edit)


    def delete_row(self, row):
        reply = QMessageBox.question(self, '确认删除', f'确定要删除第 {row + 1} 行吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            cursor = self.db_connection.cursor()
            student_name_item = self.table_widget.item(row, 0)
            if student_name_item:
                student_name = student_name_item.text()
                cursor.execute("DELETE FROM schedule WHERE student_name = ?", (student_name,))
                self.db_connection.commit()

            self.table_widget.removeRow(row)
        # Update template button text after deletion
        if self.table_widget.rowCount() == 0:
            self.init_btn.setText("生成课表模板")

    def generate_template(self):
        # Check if table has data
        if self.table_widget.rowCount() > 0:
            # Export current table data
            data = {
                '学生姓名': [],
                '课程名称': [],
                '学分': [],
                '行课时间': [],
                '教室': []
            }
            
            # Collect data from table
            for row in range(self.table_widget.rowCount()):
                # Get student name
                student_name = self.table_widget.item(row, 0)
                data['学生姓名'].append(student_name.text() if student_name else '')
                
                # Get course name from combobox
                course_combo = self.table_widget.cellWidget(row, 1)
                data['课程名称'].append(course_combo.currentText() if course_combo else '')
                
                # Get credit from line edit
                credit_edit = self.table_widget.cellWidget(row, 2)
                data['学分'].append(credit_edit.text() if credit_edit else '')
                
                # Get time slot from combobox
                time_combo = self.table_widget.cellWidget(row, 3)
                data['行课时间'].append(time_combo.currentText() if time_combo else '')
                
                # Get classroom from line edit
                classroom_edit = self.table_widget.cellWidget(row, 4)
                classroom = classroom_edit.text() if classroom_edit else ''
                # Remove 'H' prefix for export if it exists
                if classroom.startswith('H'):
                    classroom = classroom[1:]
                data['教室'].append(classroom)
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Save to Excel
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "导出课表", "", 
                                                     "Excel Files (*.xlsx);;All Files (*)", 
                                                     options=options)
            if file_name:
                try:
                    df.to_excel(file_name, index=False)
                    QMessageBox.information(self, "成功", "课表已导出")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
        
        else:
            # Generate empty template
            template_data = {
                '学生姓名': [''],
                '课程名称': [''],
                '学分': [''],
                '行课时间': [''],
                '教室': ['']
            }
            df_template = pd.DataFrame(template_data)
            
            # Save template
            options = QFileDialog.Options()
            file_name, _ = QFileDialog.getSaveFileName(self, "保存课表模板", "", 
                                                     "Excel Files (*.xlsx);;All Files (*)", 
                                                     options=options)
            if file_name:
                try:
                    df_template.to_excel(file_name, index=False)
                    QMessageBox.information(self, "成功", "课表模板已生成")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"模板生成失败: {str(e)}")
    
        # Update button text based on table content
        if self.table_widget.rowCount() > 0:
            self.template_btn.setText("导出课表")
        else:
            self.template_btn.setText("生成课表模板")

    def save_to_database(self):
        """保存当前表格数据到数据库"""
        try:
            cursor = self.db_connection.cursor()
            
            # 清空现有数据
            cursor.execute("DELETE FROM schedule")
            
            # 保存每一行数据
            for row in range(self.table_widget.rowCount()):
                # 获取各列的数据
                student_widget = self.table_widget.cellWidget(row, 0)
                course_widget = self.table_widget.cellWidget(row, 2)
                credit_widget = self.table_widget.cellWidget(row, 3)
                weekday_widget = self.table_widget.cellWidget(row, 4)
                time_widget = self.table_widget.cellWidget(row, 5)
                semester_widget = self.table_widget.cellWidget(row, 6)
                classroom_widget = self.table_widget.cellWidget(row, 7)

                # 检查必要的控件是否存在
                if not all([student_widget, course_widget]):
                    continue

                # 根据控件类型获取值
                student_name = student_widget.currentText() if isinstance(student_widget, QComboBox) else ""
                course_name = course_widget.currentText() if isinstance(course_widget, QComboBox) else ""
                credit = credit_widget.text() if isinstance(credit_widget, QLineEdit) else "0"
                weekday = weekday_widget.currentText() if isinstance(weekday_widget, QComboBox) else ""
                time_slot = time_widget.currentText() if isinstance(time_widget, QComboBox) else ""
                semester = semester_widget.text() if isinstance(semester_widget, QLineEdit) else ""
                classroom = classroom_widget.text() if isinstance(classroom_widget, QLineEdit) else ""

                # 跳过空行
                if not all([student_name, course_name]):
                    continue

                # 插入数据库
                try:
                    cursor.execute("""
                        INSERT INTO schedule 
                        (student_name, course_name, credit, weekday, time_slot, classroom, semester)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (student_name, course_name, credit, weekday, time_slot, classroom, semester))
                except sqlite3.Error as e:
                    print(f"插入行 {row + 1} 时出错: {str(e)}")
                    continue

            self.db_connection.commit()
            print("数据保存成功")
            return True

        except Exception as e:
            print(f"保存到数据库失败: {str(e)}")
            self.db_connection.rollback()
            return False

    def import_from_sqlite(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "从 SQLite 文件导入", "", "SQLite Files (*.db);;All Files (*)", options=options)
        if file_name:
            try:
                cursor = self.db_connection.cursor()
                cursor.execute("DELETE FROM schedule")
                self.db_connection.commit()

                new_conn = sqlite3.connect(file_name)
                new_cursor = new_conn.cursor()
                new_cursor.execute("SELECT student_name, course_name, credit, time_slot, classroom FROM schedule")
                rows = new_cursor.fetchall()

                cursor.executemany("""
                    INSERT INTO schedule (student_name, course_name, credit, time_slot, classroom)
                    VALUES (?, ?, ?, ?, ?)
                """, rows)
                self.db_connection.commit()
                new_conn.close()

                self.imported_file_path = file_name
                self.update_status_label("sqlite")
                self.load_schedule_into_table()
                QMessageBox.information(self, "成功", "数据已从 SQLite 文件导入")
            except sqlite3.Error as e:
                print(f"导入失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
            except Exception as e:
                print(f"导入时出现未预料的错误: {str(e)}")
                QMessageBox.critical(self, "错误", f"导入时出现未预料的错误: {str(e)}")


    def export_to_sqlite(self):
        # Save the current table data to the database
        if not self.save_to_database():
            QMessageBox.critical(self, "错误", "保存数据失败")
            return

        # Export the current database to a new SQLite file
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "导出至 SQLite 文件", "", "SQLite Files (*.db);;All Files (*)", options=options)
        if file_name:
            try:
                # Connect to the new SQLite file
                new_conn = sqlite3.connect(file_name)
                new_cursor = new_conn.cursor()
                new_cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schedule (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_name TEXT,
                        course_name TEXT,
                        credit INTEGER,
                        time_slot TEXT,
                        classroom TEXT
                    )
                """)
                new_conn.commit()

                # Copy data from the current database to the new SQLite file
                cursor = self.db_connection.cursor()
                cursor.execute("SELECT student_name, course_name, credit, time_slot, classroom FROM schedule")
                rows = cursor.fetchall()
                new_cursor.executemany("""
                    INSERT INTO schedule (student_name, course_name, credit, time_slot, classroom)
                    VALUES (?, ?, ?, ?, ?)
                """, rows)
                new_conn.commit()
                new_conn.close()
                QMessageBox.information(self, "成功", "数据已导出至 SQLite 文件")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
            except Exception as e:
                print(f"导出时出现未预料的错误: {str(e)}")
                QMessageBox.critical(self, "错误", f"导出时出现未预料的错误: {str(e)}")

    def update_dropdowns(self):
        """更新下拉列表的内容"""
        cursor = self.db_connection.cursor()
        
        # 更新学生列表
        cursor.execute("SELECT student_name FROM students")
        self.student_list = [row[0] for row in cursor.fetchall()]
        
        # 更新课程列表
        cursor.execute("SELECT course_name FROM courses")
        self.course_list = [row[0] for row in cursor.fetchall()]

    def create_student_combobox(self, current_text=""):
        """创建学生下拉框"""
        combo = QComboBox()
        combo.addItems([name.strip() for name in self.student_list])
        combo.setEditable(True)
        combo.setCurrentText(current_text.strip())

        completer = QCompleter(self.student_list, combo)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combo.setCompleter(completer)

        # 添加信号连接
        combo.currentTextChanged.connect(lambda text, c=combo: self.update_student_class(text, c))

        return combo

    def show_student_manager(self):
        self.student_manager = StudentManager(self.db_connection, self)
        self.student_manager.show()

    def show_course_manager(self):
        self.course_manager = CourseManager(self.db_connection, self)
        self.course_manager.show()

class StudentManager(QtWidgets.QDialog):
    student_updated = pyqtSignal()

    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.initUI()
        self.load_students()

    def initUI(self):
        self.setWindowTitle("学生管理")
        self.setGeometry(200, 200, 510, 400)

        layout = QVBoxLayout()

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(3)
        self.student_table.setHorizontalHeaderLabels(['学生姓名', '班级','学号'])
        layout.addWidget(self.student_table)

        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加学生")
        self.add_btn.clicked.connect(self.add_student)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑学生")
        self.edit_btn.clicked.connect(self.edit_student)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除学生")
        self.delete_btn.clicked.connect(self.delete_student)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_students(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT student_name, class_name FROM students")
        students = cursor.fetchall()

        self.student_table.setRowCount(len(students))
        for row, student in enumerate(students):
            for col, value in enumerate(student):
                item = QTableWidgetItem(str(value))
                self.student_table.setItem(row, col, item)

    def add_student(self):
        name, ok = QInputDialog.getText(self, "添加学生", "请输入学生姓名:")
        if ok and name:
            class_name, ok = QInputDialog.getText(self, "添加学生", "请输入班级:")
            if ok:
                try:
                    cursor = self.db_connection.cursor()
                    cursor.execute("INSERT INTO students (student_name, class_name) VALUES (?, ?)", (name, class_name))
                    self.db_connection.commit()
                    self.load_students()
                    self.student_updated.emit()
                    QMessageBox.information(self, "成功", "学生添加成功")
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "错误", "该学生已存在")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    def edit_student(self):
        current_row = self.student_table.currentRow()
        if current_row >= 0:
            old_name = self.student_table.item(current_row, 0).text()
            old_class = self.student_table.item(current_row, 1).text()

            name, ok = QInputDialog.getText(self, "编辑学生", "请输入新的学生姓名:", text=old_name)
            if ok and name:
                class_name, ok = QInputDialog.getText(self, "编辑学生", "请输入新的班级:", text=old_class)
                if ok:
                    try:
                        cursor = self.db_connection.cursor()
                        cursor.execute("UPDATE students SET student_name = ?, class_name = ? WHERE student_name = ?", (name, class_name, old_name))
                        self.db_connection.commit()
                        self.load_students()
                        self.student_updated.emit()
                        QMessageBox.information(self, "成功", "学生信息更新成功")
                    except sqlite3.IntegrityError:
                        QMessageBox.warning(self, "错误", "该学生已存在")
                    except Exception as e:
                        QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")

    def delete_student(self):
        current_row = self.student_table.currentRow()
        if current_row >= 0:
            student_name = self.student_table.item(current_row, 0).text()

            reply = QMessageBox.question(self, '确认删除', f'确定要删除学生 {student_name} 吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    cursor = self.db_connection.cursor()
                    cursor.execute("DELETE FROM students WHERE student_name = ?", (student_name,))
                    self.db_connection.commit()
                    self.load_students()
                    self.student_updated.emit()
                    QMessageBox.information(self, "成功", "学生删除成功")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

class CourseManager(QtWidgets.QDialog):
    course_updated = pyqtSignal()

    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.parent = parent
        self.course_dict = {}  # 添加一个字典来存储课程名称和学分
        self.initUI()
        self.load_courses()

    def initUI(self):
        self.setWindowTitle("课程管理")
        self.setGeometry(200, 200, 520, 400)

        layout = QVBoxLayout()

        self.course_table = QTableWidget()
        self.course_table.setColumnCount(3)
        self.course_table.setHorizontalHeaderLabels(['课程名称', '学分', '周数'])
        layout.addWidget(self.course_table)

        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("添加课程")
        self.add_btn.clicked.connect(self.add_course)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("编辑课程")
        self.edit_btn.clicked.connect(self.edit_course)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("删除课程")
        self.delete_btn.clicked.connect(self.delete_course)
        button_layout.addWidget(self.delete_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_courses(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT course_name, credit, semester FROM courses")
        courses = cursor.fetchall()

        self.course_table.setRowCount(len(courses))
        self.course_dict = {course[0]: course[1] for course in courses}  # 课程名称和学分绑定
        for row, course in enumerate(courses):
            for col, value in enumerate(course):
                item = QTableWidgetItem(str(value))
                self.course_table.setItem(row, col, item)

    def add_course(self):
        course_list = [
            "高等数学", "线性代数", "大学物理", "大学物理实验", "工程数学", "大学物理", 
            "大学物理实验", "概率论与数理统计", "工程导论", "c语言编程与实践", "电路分析基础", 
            "工程实践", "金工实习", "工程制图", "模拟电子技术", "运筹学", "数字电路与逻辑设计", 
            "信号与系统", "自动控制原理", "电子系统设计与实现", "微处理器与微计算机系统", 
            "传感器与检测技术", "现代控制理论", "面向对象程序设计(C++)", "机械学基础", 
            "机器人操作系统基础", "机器人系统软件设计", "机器人学基础", "人工智能", 
            "机器人设计与实现", "Python编程技术", "系统仿真编程技术", "嵌入式系统原理与设计", 
            "图像处理与机器视觉", "模式识别与机器学习", "无人驾驶技术", "三维建模及仿真", 
            "机器人控制元件与控制系", "移动机器人定位与导航", "思想道德与法治", "中国近现代史纲要", 
            "形势与政策", "马克思主义基本原理", "毛泽东思想和中国特色社会", 
            "义理论体系概论", "习近平新时代中国特色社会主义思想概论", "大学英语", 
            "创新创业教育基础", "TRIZ创新方法", "创业培训", "创新、发明与知识产权实践"
        ]

        dialog = SelectCourseDialog(course_list)
        if dialog.exec_() == QDialog.Accepted:
            selected_course = dialog.selected_course
            if selected_course:
                credit, ok = QInputDialog.getDouble(self, "添加课程", "请输入学分:", 0, 0, 20, 1, Qt.WindowFlags(), 0.5)  # 添加step=0.5
                if ok:
                    semester, ok = QInputDialog.getText(self, "添加课程", "请输入周数\n(例如: 第1至17周):")
                    if ok:
                        try:
                            cursor = self.db_connection.cursor()
                            cursor.execute("""
                                INSERT INTO courses (course_name, credit, semester)
                                VALUES (?, ?, ?)
                            """, (selected_course, credit, semester))
                            self.db_connection.commit()
                            self.load_courses()
                            self.course_updated.emit()
                            QMessageBox.information(self, "成功", "课程添加成功")
                        except sqlite3.IntegrityError:
                            QMessageBox.warning(self, "错误", "该课程已存在")
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")

    def edit_course(self):
        current_row = self.course_table.currentRow()
        if current_row >= 0:
            old_name = self.course_table.item(current_row, 0).text()
            old_credit = float(self.course_table.item(current_row, 1).text())
            old_semester = self.course_table.item(current_row, 2).text()

            name, ok = QInputDialog.getText(self, "编辑课程", "请输入新的课程名称:", text=old_name)
            if ok and name:
                credit, ok = QInputDialog.getDouble(self, "编辑课程", "请输入新的学分:", old_credit, 0, 20, 1, Qt.WindowFlags(), 0.5)  # 添加step=0.5
                if ok:
                    semester, ok = QInputDialog.getText(self, "编辑课程", "请输入持续周数:", text=old_semester)
                    if ok:
                        try:
                            cursor = self.db_connection.cursor()
                            cursor.execute("""
                                UPDATE courses 
                                SET course_name = ?, credit = ?, semester = ?
                                WHERE course_name = ?
                            """, (name, credit, semester, old_name))
                            self.db_connection.commit()
                            self.load_courses()
                            self.course_updated.emit()
                            QMessageBox.information(self, "成功", "课程信息更新成功")
                        except sqlite3.IntegrityError:
                            QMessageBox.warning(self, "错误", "该课程已存在")
                        except Exception as e:
                            QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")

    def delete_course(self):
        current_row = self.course_table.currentRow()
        if current_row >= 0:
            course_name = self.course_table.item(current_row, 0).text()

            reply = QMessageBox.question(self, '确认删除', f'确定要删除课程 {course_name} 吗？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    cursor = self.db_connection.cursor()
                    cursor.execute("DELETE FROM courses WHERE course_name = ?", (course_name,))
                    self.db_connection.commit()
                    self.load_courses()
                    self.course_updated.emit()
                    QMessageBox.information(self, "成功", "课程删除成功")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def create_course_combobox(self, current_text=""):
        """创建课程下拉框"""
        combo = QComboBox()
        combo.addItems(self.course_list)
        combo.setEditable(True)
        combo.setCurrentText(current_text)

        completer = QCompleter(self.course_list, combo)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combo.setCompleter(completer)

        # 添加信号连接
        combo.currentTextChanged.connect(lambda text, c=combo: self.update_course_info(text, c))

        return combo

class SelectCourseDialog(QDialog):
    def __init__(self, course_list, parent=None):
        super().__init__(parent)
        self.course_list = course_list
        self.selected_course = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("选择课程")
        self.setFixedSize(1360, 507) 

        layout = QVBoxLayout()

        # 创建表格
        self.course_table = QTableWidget()
        self.course_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 设置为不可编辑
        
        # 计算行数和列数
        total_courses = len(self.course_list)
        num_columns = 6
        num_rows = (total_courses + num_columns - 1) // num_columns
        
        self.course_table.setColumnCount(num_columns)
        self.course_table.setRowCount(num_rows)
        
        # 隐藏表头
        self.course_table.horizontalHeader().hide()
        self.course_table.verticalHeader().hide()
        
        # 填充课程
        for index, course in enumerate(self.course_list):
            row = index // num_columns
            col = index % num_columns
            item = QTableWidgetItem(course)
            item.setTextAlignment(Qt.AlignCenter)  # 居中对齐
            self.course_table.setItem(row, col, item)
        
        # 自适应列宽
        self.course_table.resizeColumnsToContents()
        
        # 双击选择
        self.course_table.itemDoubleClicked.connect(self.select_course)
        
        layout.addWidget(self.course_table)

        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.select_btn = QPushButton("选择")
        self.select_btn.clicked.connect(self.select_course_btn)
        button_layout.addWidget(self.select_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def select_course_btn(self):
        """通过按钮选择课程"""
        current_item = self.course_table.currentItem()
        if current_item:
            self.selected_course = current_item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请先选择一个课程")

    def select_course(self, item):
        """通过双击选择课程"""
        self.selected_course = item.text()
        self.accept()

if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication(sys.argv)
        mainWin = ScheduleManager()
        mainWin.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动错误: {str(e)}")
