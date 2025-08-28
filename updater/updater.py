import sys
import os
import subprocess
import time
import shutil
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap

class UpdateWorker(QThread):
    """アップデート処理を行うワーカースレッド"""
    progress_signal = pyqtSignal(int, str)  # 進捗％, メッセージ
    finished_signal = pyqtSignal(bool, str)  # 成功/失敗, メッセージ
    
    def __init__(self, new_exe_path, current_exe_name):
        super().__init__()
        self.new_exe_path = new_exe_path
        self.current_exe_name = current_exe_name
    
    def run(self):
        """アップデート処理を実行"""
        try:
            # [1/5] アップデート準備
            self.progress_signal.emit(10, "アップデート準備中...")
            time.sleep(0.5)
            
            # 新しいexeファイルが存在するかチェック
            if not os.path.exists(self.new_exe_path):
                self.finished_signal.emit(False, f"新しいexeファイルが見つかりません: {self.new_exe_path}")
                return
            
            # [2/5] プロセス終了を待機
            self.progress_signal.emit(25, "プロセス終了を待機中...")
            time.sleep(2)  # プロセス終了を待機
            
            # [3/5] バックアップ作成
            self.progress_signal.emit(45, "バックアップ作成中...")
            backup_path = f"{self.current_exe_name}.backup"
            if os.path.exists(self.current_exe_name):
                try:
                    shutil.copy2(self.current_exe_name, backup_path)
                except Exception as e:
                    self.finished_signal.emit(False, f"バックアップの作成に失敗しました: {str(e)}")
                    return
            
            # [4/5] ファイル置換
            self.progress_signal.emit(70, "ファイル置換中...")
            try:
                shutil.copy2(self.new_exe_path, self.current_exe_name)
            except Exception as e:
                # エラー時はバックアップから復元
                if os.path.exists(backup_path):
                    try:
                        shutil.copy2(backup_path, self.current_exe_name)
                        self.finished_signal.emit(False, f"ファイル置換に失敗しました。バックアップから復元しました: {str(e)}")
                    except:
                        self.finished_signal.emit(False, f"ファイル置換とバックアップ復元の両方に失敗しました: {str(e)}")
                else:
                    self.finished_signal.emit(False, f"ファイル置換に失敗しました: {str(e)}")
                return
            
            # [5/5] 一時ファイルのクリーンアップ
            self.progress_signal.emit(90, "一時ファイルのクリーンアップ中...")
            
            # ダウンロードした一時ファイルを削除
            if os.path.exists(self.new_exe_path):
                try:
                    os.remove(self.new_exe_path)
                except:
                    pass  # 削除できなくても続行
            
            # バックアップファイルを削除
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except:
                    pass  # 削除できなくても続行
            
            # temp_updateフォルダを削除
            if os.path.exists("temp_update"):
                try:
                    shutil.rmtree("temp_update")
                except:
                    pass  # 削除できなくても続行
            
            # .update_completedファイルを削除
            if os.path.exists(".update_completed"):
                try:
                    os.remove(".update_completed")
                except:
                    pass  # 削除できなくても続行
            
            # 完了
            self.progress_signal.emit(100, "アップデート完了！")
            time.sleep(0.5)
            self.finished_signal.emit(True, "ClipItBroが最新版に更新されました。")
            
            # 新しいClipItBro.exeを自動起動
            try:
                subprocess.Popen([self.current_exe_name], cwd=os.getcwd())
            except Exception as e:
                print(f"新しいexeファイルの起動エラー: {e}")
            
        except Exception as e:
            self.finished_signal.emit(False, f"予期しないエラーが発生しました: {str(e)}")

class UpdaterWindow(QWidget):
    """アップデーターのメインウィンドウ"""
    
    def __init__(self, new_exe_path, current_exe_name):
        super().__init__()
        self.new_exe_path = new_exe_path
        self.current_exe_name = current_exe_name
        self.worker = None
        self.init_ui()
        self.start_update()
    
    def init_ui(self):
        """UIを初期化"""
        self.setWindowTitle("ClipItBro アップデーター")
        self.setFixedSize(400, 180)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        # アイコン設定を試行（存在しない場合はスキップ）
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon", "updater_app.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass
        
        # レイアウト作成
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # タイトル
        title_label = QLabel("ClipItBro アップデーター")
        title_font = QFont("Yu Gothic UI", 12, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFixedHeight(25)
        title_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title_label)
        
        # サブタイトル
        subtitle_label = QLabel("by 菊池組")
        subtitle_font = QFont("Yu Gothic UI", 8)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setFixedHeight(18)
        subtitle_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(subtitle_label)
        
        # 進捗メッセージ
        self.status_label = QLabel("準備中...")
        status_font = QFont("Yu Gothic UI", 9)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(22)
        self.status_label.setStyleSheet("""
            color: #34495e;
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 3px;
            padding: 2px;
        """)
        layout.addWidget(self.status_label)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                text-align: center;
                font-size: 10px;
                font-family: "Yu Gothic UI";
                background-color: #ecf0f1;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 閉じるボタン（最初は無効）
        self.close_button = QPushButton("閉じる")
        self.close_button.setEnabled(False)
        self.close_button.setFixedHeight(28)
        button_font = QFont("Yu Gothic UI", 9)
        self.close_button.setFont(button_font)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                border: none;
                color: white;
                border-radius: 4px;
                font-size: 9px;
                font-family: "Yu Gothic UI";
            }
            QPushButton:enabled {
                background-color: #3498db;
            }
            QPushButton:enabled:hover {
                background-color: #2980b9;
            }
            QPushButton:enabled:pressed {
                background-color: #21618c;
            }
        """)
        self.close_button.clicked.connect(self.close)
        
        layout.addWidget(self.close_button)
        
        self.setLayout(layout)
        
        # ウィンドウの背景色設定
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
        """)
        
        # ウィンドウを中央に配置
        self.center_window()
    
    def center_window(self):
        """ウィンドウを画面中央に配置"""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def start_update(self):
        """アップデート処理を開始"""
        self.worker = UpdateWorker(self.new_exe_path, self.current_exe_name)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.update_finished)
        self.worker.start()
    
    def update_progress(self, progress, message):
        """進捗を更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def update_finished(self, success, message):
        """アップデート完了時の処理"""
        if success:
            self.status_label.setText("✓ " + message)
            self.status_label.setStyleSheet("""
                color: #27ae60;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                padding: 2px;
            """)
            
            # 3秒後に自動で閉じる
            self.close_timer = QTimer()
            self.close_timer.timeout.connect(self.close)
            self.close_timer.start(3000)
            
            # カウントダウン表示
            self.countdown = 3
            self.countdown_timer = QTimer()
            self.countdown_timer.timeout.connect(self.update_countdown)
            self.countdown_timer.start(1000)
            
        else:
            self.status_label.setText("✗ " + message)
            self.status_label.setStyleSheet("""
                color: #e74c3c;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 3px;
                padding: 2px;
            """)
            self.close_button.setEnabled(True)
    
    def update_countdown(self):
        """カウントダウン表示を更新"""
        self.close_button.setText(f"閉じる ({self.countdown}秒)")
        self.countdown -= 1
        if self.countdown < 0:
            self.countdown_timer.stop()
            self.close_button.setText("閉じる")

def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # 引数チェック
    if len(sys.argv) != 3:
        QMessageBox.critical(None, "エラー", 
                           "使用法: updater.exe <新しいexeファイルのパス> <現在のexeファイル名>\n"
                           "このプログラムはClipItBro.exeから自動的に呼び出されます。")
        sys.exit(1)
    
    new_exe_path = sys.argv[1]
    current_exe_name = sys.argv[2]
    
    # アップデーターウィンドウを表示
    window = UpdaterWindow(new_exe_path, current_exe_name)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
