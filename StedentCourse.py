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

    def initUI(self):
        self.setWindowTitle("学生课表管理程序")
        self.setGeometry(100, 100, 1000, 600)

        # Status Label
        self.status_label = QLabel("等待导入表格中", self)
        self.status_label.setGeometry(50, 10, 900, 30)
        self.status_label.setStyleSheet("color: gray;")

        # Table Widget
        self.table_widget = QTableWidget(self)
        self.table_widget.setGeometry(50, 50, 900, 400)
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(['学生姓名', '课程名称', '学分', '行课时间', '教室'])
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
        # 根据按钮文本决定执行的操作
        if self.init_btn.text() == "导出课表":
            self.export_to_excel()
            return
    
        # 执行初始化操作
        reply = QMessageBox.question(self, '确认初始化', 
                                   '这将清空所有现有的学生和课程信息，确定要继续吗？',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                cursor = self.db_connection.cursor()
                
                # 清空现有数据
                cursor.execute("DELETE FROM schedule")
                cursor.execute("DELETE FROM students")
                cursor.execute("DELETE FROM courses")
                
                # 重置自增ID
                cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('students', 'courses', 'schedule')")
                
                # 初始化默认学生
                default_students = [
                    ('张三', '计算机2101'),
                    ('李四', '计算机2101'),
                    ('王五', '计算机2102'),
                    # ... 可以添加更多默认学生
                ]
                cursor.executemany("""
                    INSERT INTO students (student_name, class_name)
                    VALUES (?, ?)
                """, default_students)
                
                # 初始化默认课程
                default_courses = [
                    ('高等数学', 4.0, '3-16'),
                    ('线性代数', 3.0, '3-14'),
                    ('大学物理', 4.0, '6-15'),
                    ('Python编程技术', 2.5, '3-16'),
                    ('思想道德与法治', 3.5, '9-14'),
                ]
                cursor.executemany("""
                    INSERT INTO courses (course_name, credit, semester)
                    VALUES (?, ?, ?)
                """, default_courses)
                
                self.db_connection.commit()
                
                # 清空并重新加载表格
                self.table_widget.setRowCount(0)
                self.load_courses()
                
                QMessageBox.information(self, "成功", "学生与课程信息已初始化")
                
            except Exception as e:
                self.db_connection.rollback()
                QMessageBox.critical(self, "错误", f"初始化失败: {str(e)}")
                return
            
            # 更新状态标签
            self.status_label.setText("数据已初始化")
            self.status_label.setStyleSheet("color: blue;")
    
    def export_to_excel(self):
        """导出课表到Excel文件"""
        try:
            # 收集表格数据
            data = {
                '学生姓名': [],
                '课程名称': [],
                '学分': [],
                '行课时间': [],
                '教室': []
            }
            
            # 从表格中获取数据
            for row in range(self.table_widget.rowCount()):
                # 获取学生姓名
                student_combo = self.table_widget.cellWidget(row, 0)
                data['学生姓名'].append(student_combo.currentText() if student_combo else '')
                
                # 获取课程名称
                course_combo = self.table_widget.cellWidget(row, 1)
                data['课程名称'].append(course_combo.currentText() if course_combo else '')
                
                # 获取学分
                credit_edit = self.table_widget.cellWidget(row, 2)
                data['学分'].append(credit_edit.text() if credit_edit else '')
                
                # 获取行课时间
                time_combo = self.table_widget.cellWidget(row, 3)
                data['行课时间'].append(time_combo.currentText() if time_combo else '')
                
                # 获取教室
                classroom_edit = self.table_widget.cellWidget(row, 4)
                classroom = classroom_edit.text() if classroom_edit else ''
                # 移除'H'前缀用于导出
                if classroom.startswith('H'):
                    classroom = classroom[1:]
                data['教室'].append(classroom)
            
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
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def connect_to_database(self):
        try:
            conn = sqlite3.connect("schedule.db")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT,
                    course_name TEXT,
                    credit INTEGER,
                    time_slot TEXT,
                    classroom TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT UNIQUE,
                    class_name TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_name TEXT UNIQUE,
                    credit INTEGER,
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
            student_combo = self.create_student_combobox(self.table_widget.item(row, 0).text())
            self.table_widget.setCellWidget(row, 0, student_combo)
            course_combo = self.create_course_combobox(self.table_widget.item(row, 1).text())
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
        cursor.execute("SELECT student_name, course_name, credit, time_slot, classroom FROM schedule")
        rows = cursor.fetchall()

        for row_data in rows:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)
            for column, data in enumerate(row_data):
                if isinstance(data, bytes):
                    data = data.decode('utf-8')  # Decode bytes to string

                if column == 1:  # Assuming course_name is at index 1
                    combo = self.create_course_combobox(data)
                    self.table_widget.setCellWidget(row_position, column, combo)
                elif column == 2:  # Credit column
                    line_edit = QLineEdit(str(data))
                    line_edit.setValidator(QIntValidator(0, 100))  # Allow only numbers
                    self.table_widget.setCellWidget(row_position, column, line_edit)
                elif column == 3:  # Time slot column
                    combo = self.create_time_slot_combobox(data)
                    self.table_widget.setCellWidget(row_position, column, combo)
                elif column == 4:  # Classroom column
                    line_edit = QLineEdit(str(data))
                    line_edit.setValidator(QIntValidator(0, 9999))  # Allow only numbers
                    line_edit.editingFinished.connect(lambda le=line_edit: self.add_classroom_prefix(le))
                    self.table_widget.setCellWidget(row_position, column, line_edit)
                else:
                    self.table_widget.setItem(row_position, column, QTableWidgetItem(str(data)))
        self.init_btn.setText("导出课表")

    def create_course_combobox(self, current_text=""):
        combo = QComboBox()
        combo.addItems(self.course_list)
        combo.setEditable(True)
        combo.setCurrentText(current_text)

        completer = QCompleter(self.course_list, combo)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        combo.setCompleter(completer)

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

    def add_classroom_prefix(self, line_edit):
        text = line_edit.text()
        if not text.startswith('H'):
            line_edit.setText(f'H{text}')

    def add_new_row(self):
        row_position = self.table_widget.rowCount()
        self.table_widget.insertRow(row_position)

        for column in range(self.table_widget.columnCount()):
            if column == 0:  # Assuming student_name is at index 0
                combo = self.create_student_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 1:  # Assuming course_name is at index 1
                combo = self.create_course_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 2:  # Credit column
                line_edit = QLineEdit()
                line_edit.setValidator(QIntValidator(0, 100))  # Allow only numbers
                self.table_widget.setCellWidget(row_position, column, line_edit)
            elif column == 3:  # Time slot column
                combo = self.create_time_slot_combobox()
                self.table_widget.setCellWidget(row_position, column, combo)
            elif column == 4:  # Classroom column
                line_edit = QLineEdit()
                line_edit.setValidator(QIntValidator(0, 9999))  # Allow only numbers
                line_edit.editingFinished.connect(lambda le=line_edit: self.add_classroom_prefix(le))
                self.table_widget.setCellWidget(row_position, column, line_edit)
            else:
                self.table_widget.setItem(row_position, column, QTableWidgetItem(""))

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
        """Save current table data to database"""
        try:
            cursor = self.db_connection.cursor()
            
            # Clear existing data
            cursor.execute("DELETE FROM schedule")
            
            # Save each row
            for row in range(self.table_widget.rowCount()):
                # Get student name
                student_name = self.table_widget.cellWidget(row, 0).currentText()
                
                # Get course name from combobox
                course_name = self.table_widget.cellWidget(row, 1).currentText()
                
                # Get credit from line edit
                credit = self.table_widget.cellWidget(row, 2).text()
                
                # Get time slot from combobox
                time_slot = self.table_widget.cellWidget(row, 3).currentText()
                
                # Get classroom from line edit
                classroom = self.table_widget.cellWidget(row, 4).text()
                
                # Insert into database
                cursor.execute("""
                    INSERT INTO schedule (student_name, course_name, credit, time_slot, classroom)
                    VALUES (?, ?, ?, ?, ?)
                """, (student_name, course_name, credit, time_slot, classroom))
            
            self.db_connection.commit()
            return True
        except Exception as e:
            print(f"保存到数据库失败: {str(e)}")
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
        combo.addItems(self.student_list)
        combo.setEditable(True)
        combo.setCurrentText(current_text)
        
        completer = QCompleter(self.student_list)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        combo.setCompleter(completer)
        
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
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(2)
        self.student_table.setHorizontalHeaderLabels(['学生姓名', '班级'])
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
        self.initUI()
        self.load_courses()

    def initUI(self):
        self.setWindowTitle("课程管理")
        self.setGeometry(200, 200, 800, 400)

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
                credit, ok = QInputDialog.getDouble(self, "添加课程", "请输入学分:", 0, 0, 100, 0.5)
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
                credit, ok = QInputDialog.getDouble(self, "编辑课程", "请输入新的学分:", old_credit, 0, 100, 1)
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

# 使用这个对话框类到 CourseManager 中
class CourseManager(QtWidgets.QDialog):
    course_updated = pyqtSignal()

    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.parent = parent
        self.initUI()
        self.load_courses()

    def initUI(self):
        self.setWindowTitle("课程管理")
        self.setGeometry(200, 200, 800, 400)

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
                credit, ok = QInputDialog.getDouble(
                    self,           # parent
                    "添加课程",      # title
                    "请输入学分:",   # label
                    0,             # default value
                    0,             # minimum value
                    100,           # maximum value
                    1,             # decimals (整数)
                    Qt.WindowFlags(),  # flags
                    0.5            # step
                )
                if ok:
                    semester, ok = QInputDialog.getText(self, "添加课程", "请输入周数:")
                    if ok:
                        # 移除可能存在的"周"字后再保存
                        semester = semester.rstrip('周')
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
                credit, ok = QInputDialog.getDouble(self, "编辑课程", "请输入新的学分:", old_credit, 0, 100, 1)
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
                    
if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication(sys.argv)
        mainWin = ScheduleManager()
        mainWin.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动错误: {str(e)}")
