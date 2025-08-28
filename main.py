import sys
import os
import subprocess
import json
import datetime
import platform
import random
import glob
import ctypes
import webbrowser
import urllib.request
import urllib.error
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QProgressBar, QMessageBox, QMenuBar, QAction, QDialog, QMenu, QActionGroup, QSystemTrayIcon
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont, QMovie

# アプリケーション情報
APP_NAME = "ClipItBro"
APP_VERSION = "1.1.1"
APP_DEVELOPER = "菊池組"
APP_COPYRIGHT = "2025"

def get_ffmpeg_executable_path(executable_name):
    """
    FFmpeg実行ファイルのパスを取得（単一exe環境対応）
    
    Args:
        executable_name (str): 実行ファイル名 ('ffmpeg.exe', 'ffprobe.exe', など)
    
    Returns:
        str: FFmpeg実行ファイルの絶対パス
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller単一exe環境：実行ファイルと同じディレクトリのbinフォルダ
        exe_dir = os.path.dirname(sys.executable)
    else:
        # 開発環境：スクリプトと同じディレクトリ
        exe_dir = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(exe_dir, 'bin', executable_name)

# Windows タスクバープログレス用のインポート（利用可能性をチェック）
try:
    from PyQt5.QtWinExtras import QWinTaskbarButton, QWinTaskbarProgress
    TASKBAR_AVAILABLE = True
except ImportError:
    # WinExtrasが利用できない場合はctypesで代替実装
    TASKBAR_AVAILABLE = False

def set_titlebar_theme(window_handle, is_dark_mode):
    """
    タイトルバーのテーマを設定（Windows専用）
    window_handle: ウィンドウハンドル
    is_dark_mode: True=ダーク, False=ライト
    """
    if sys.platform == "win32":
        try:
            # Windows 10 Build 1809以降で利用可能
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = 1 if is_dark_mode else 0
            
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                int(window_handle),
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(value)),
                ctypes.sizeof(ctypes.c_int)
            )
            return result == 0  # 0 = 成功
        except Exception as e:
            print(f"タイトルバーテーマ設定エラー: {e}")
            return False
    return False

class TaskbarProgress:
    """Windowsタスクバープログレスバー管理クラス"""
    
    def __init__(self, main_window=None):
        self.main_window = main_window
        self.taskbar_button = None
        self.taskbar_progress = None
        self.initialized = False
        
        # PyQt5 WinExtrasが利用可能かチェック
        if TASKBAR_AVAILABLE and platform.system() == "Windows":
            try:
                self.taskbar_button = QWinTaskbarButton()
                if main_window:
                    self.taskbar_button.setWindow(main_window.windowHandle())
                self.taskbar_progress = self.taskbar_button.progress()
                self.initialized = True
                print("タスクバープログレス初期化成功 (PyQt5 WinExtras)")
                
            except Exception as e:
                print(f"PyQt5 WinExtras初期化エラー: {e}")
                self.initialized = False
        
        # PyQt5 WinExtrasが利用できない場合のフォールバック
        if not self.initialized and platform.system() == "Windows":
            try:
                # Windows API直接呼び出し準備
                self.user32 = ctypes.windll.user32
                self.shell32 = ctypes.windll.shell32
                self.ole32 = ctypes.windll.ole32
                self.hwnd = None
                self.initialized = True
                print("タスクバープログレス初期化成功 (ctypes fallback)")
                
            except Exception as e:
                print(f"ctypes初期化エラー: {e}")
                self.initialized = False
        
        if not self.initialized:
            print("タスクバープログレス機能は利用できません")
    
    def set_window(self, main_window):
        """メインウィンドウを設定"""
        self.main_window = main_window
        
        if TASKBAR_AVAILABLE and self.taskbar_button and main_window:
            try:
                self.taskbar_button.setWindow(main_window.windowHandle())
                self.initialized = True
                print("タスクバープログレス ウィンドウ設定完了 (PyQt5)")
            except Exception as e:
                print(f"PyQt5 ウィンドウ設定エラー: {e}")
        
        # ctypes版の場合はウィンドウハンドルを取得
        if not TASKBAR_AVAILABLE and main_window and self.initialized:
            try:
                self.hwnd = int(main_window.winId())
                print(f"タスクバープログレス ウィンドウハンドル設定: {self.hwnd}")
            except Exception as e:
                print(f"ウィンドウハンドル取得エラー: {e}")
    
    def set_progress(self, value, maximum=100):
        """プログレス値を設定 (0-maximum)"""
        if not self.initialized:
            return False
        
        # PyQt5 WinExtras版
        if TASKBAR_AVAILABLE and self.taskbar_progress:
            try:
                self.taskbar_progress.setMaximum(maximum)
                self.taskbar_progress.setValue(value)
                self.taskbar_progress.setVisible(True)
                return True
            except Exception as e:
                print(f"PyQt5タスクバープログレス設定エラー: {e}")
                return False
        
        # ctypes版（フォールバック）
        elif self.hwnd:
            try:
                # 簡単な進捗表示（Windows API直接呼び出し）
                # 実際の実装は複雑なCOMインターフェースが必要なため、
                # ここでは基本的な進捗状態のみ設定
                progress_percent = (value * 100) // maximum
                # ウィンドウタイトルに進捗を表示（簡易版）
                if self.main_window:
                    title = f"{APP_NAME} {APP_VERSION} - {progress_percent}%"
                    self.main_window.setWindowTitle(title)
                return True
            except Exception as e:
                print(f"ctypesタスクバープログレス設定エラー: {e}")
                return False
        
        return False
    
    def set_visible(self, visible):
        """プログレスバーの表示/非表示を切り替え"""
        if not self.initialized:
            return False
        
        # PyQt5 WinExtras版
        if TASKBAR_AVAILABLE and self.taskbar_progress:
            try:
                self.taskbar_progress.setVisible(visible)
                return True
            except Exception as e:
                print(f"PyQt5タスクバープログレス表示切り替えエラー: {e}")
                return False
        
        # ctypes版（フォールバック）
        elif self.main_window:
            try:
                if not visible:
                    # 進捗表示をクリア
                    self.main_window.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
                return True
            except Exception as e:
                print(f"ctypesタスクバープログレス表示切り替えエラー: {e}")
                return False
        
        return False
    
    def clear_progress(self):
        """プログレスをクリア"""
        return self.set_visible(False)
    
    def set_paused(self, paused=True):
        """一時停止状態を設定"""
        if not self.initialized:
            return False
        
        # PyQt5 WinExtras版
        if TASKBAR_AVAILABLE and self.taskbar_progress:
            try:
                self.taskbar_progress.setPaused(paused)
                return True
            except Exception as e:
                print(f"PyQt5タスクバープログレス一時停止設定エラー: {e}")
                return False
        
        # ctypes版は一時停止状態の設定は省略
        return True

class UpdateChecker(QThread):
    """アップデート確認クラス"""
    update_available_signal = pyqtSignal(str)  # 新しいバージョンが利用可能
    update_check_failed_signal = pyqtSignal(str)  # チェック失敗
    unreleased_version_signal = pyqtSignal(str)  # 未公開バージョン
    up_to_date_signal = pyqtSignal()  # 最新版
    
    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version
        # GitHub Releases APIを使用して最新バージョンを取得
        self.releases_api_url = "https://api.github.com/repos/EpicJunriel/KIK-ClipItBro/releases/latest"
        self.release_notes = None  # リリースノートを保存
    
    def get_release_notes(self, version):
        """指定されたバージョンのリリースノートをダウンロード"""
        try:
            # GitHubのRawファイルURLを構築（RELEASE_NOTES.txtと同じ場所に配置）
            notes_url = f"https://github.com/EpicJunriel/KIK-ClipItBro/releases/download/{version}/RELEASE_NOTES.txt"
            
            request = urllib.request.Request(notes_url)
            request.add_header('User-Agent', f'{APP_NAME}/{self.current_version}')
            
            with urllib.request.urlopen(request, timeout=5) as response:
                content = response.read().decode('utf-8', errors='ignore')
                return content.strip()
        except Exception:
            # リリースノートが見つからない場合はデフォルトメッセージ
            return "このバージョンの詳細情報は、GitHubのリリースページでご確認ください。"
    
    def run(self):
        """バックグラウンドでアップデートをチェック"""
        try:
            # GitHub Releases APIから最新リリース情報を取得
            request = urllib.request.Request(self.releases_api_url)
            request.add_header('User-Agent', f'{APP_NAME}/{self.current_version}')
            request.add_header('Accept', 'application/vnd.github+json')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                latest_version = data.get('tag_name', '').strip()
                
                if not latest_version:
                    self.update_check_failed_signal.emit("最新バージョン情報が取得できませんでした")
                    return
                
                # バージョン比較
                comparison_result = self.compare_versions(latest_version, self.current_version)
                
                if comparison_result > 0:
                    # リリース版の方が新しい場合
                    self.release_notes = self.get_release_notes(latest_version)
                    self.update_available_signal.emit(latest_version)
                elif comparison_result < 0:
                    # 現在のバージョンの方が新しい場合（未公開バージョン）
                    self.unreleased_version_signal.emit(latest_version)
                else:
                    # comparison_result == 0 の場合（最新版）
                    self.up_to_date_signal.emit()
                    
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.update_check_failed_signal.emit("リリース情報が見つかりませんでした")
            else:
                self.update_check_failed_signal.emit(f"GitHub API エラー: {e.code}")
        except urllib.error.URLError as e:
            self.update_check_failed_signal.emit(f"ネットワークエラー: {str(e)}")
        except json.JSONDecodeError as e:
            self.update_check_failed_signal.emit(f"レスポンス解析エラー: {str(e)}")
        except Exception as e:
            self.update_check_failed_signal.emit(f"アップデート確認エラー: {str(e)}")
    
    def compare_versions(self, version1, version2):
        """バージョン比較（version1 > version2 なら正の値、version1 < version2 なら負の値、同じなら0を返す）"""
        try:
            # バージョン番号をピリオドで分割して数値として比較
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 長さを合わせる（短い方に0を追加）
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            # 各部分を比較
            for v1_part, v2_part in zip(v1_parts, v2_parts):
                if v1_part > v2_part:
                    return 1
                elif v1_part < v2_part:
                    return -1
            
            return 0  # 同じバージョン
            
        except (ValueError, AttributeError):
            # バージョン形式が正しくない場合は文字列として比較
            if version1 > version2:
                return 1
            elif version1 < version2:
                return -1
            else:
                return 0
    
    def is_newer_version(self, latest, current):
        """バージョン比較（新しいバージョンかどうかを判定）- 後方互換性のため残す"""
        return self.compare_versions(latest, current) > 0

class UpdateDownloader(QThread):
    """アップデートファイルダウンローダー"""
    download_progress_signal = pyqtSignal(int)  # ダウンロード進捗 (0-100)
    download_finished_signal = pyqtSignal(str)  # ダウンロード完了（保存先パス）
    download_error_signal = pyqtSignal(str)     # ダウンロードエラー
    
    def __init__(self, version, save_path):
        super().__init__()
        self.version = version
        self.save_path = save_path
        self.is_cancelled = False
        self.download_url = None
    
    def cancel_download(self):
        """ダウンロードをキャンセル"""
        self.is_cancelled = True
    
    def get_github_release_exe_url(self, version):
        """GitHub Releasesから指定バージョンのexeファイルのダウンロードURLを取得"""
        try:
            # GitHub Releases API URL
            api_url = f"https://api.github.com/repos/EpicJunriel/KIK-ClipItBro/releases/tags/{version}"
            
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', f'{APP_NAME}/{APP_VERSION}')
            request.add_header('Accept', 'application/vnd.github+json')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                # assetsから "ClipItBro.exe" を最優先で探す
                for asset in data.get('assets', []):
                    if asset['name'] == 'ClipItBro.exe':
                        return asset['browser_download_url']
                
                # 次に、exeファイルで "ClipItBro" を含むものを探す
                for asset in data.get('assets', []):
                    if asset['name'].endswith('.exe') and 'ClipItBro' in asset['name']:
                        return asset['browser_download_url']
                
                # exeファイルが見つからない場合のエラー
                available_assets = [asset['name'] for asset in data.get('assets', [])]
                raise Exception(f"バージョン {version} に ClipItBro.exe が見つかりません。利用可能なファイル: {available_assets}")
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception(f"バージョン {version} のリリースが見つかりません")
            else:
                raise Exception(f"GitHub API エラー: {e.code}")
        except Exception as e:
            raise Exception(f"リリース情報取得エラー: {str(e)}")
    
    def run(self):
        """バックグラウンドでファイルをダウンロード"""
        try:
            # GitHub Releasesから実際のダウンロードURLを取得
            self.download_url = self.get_github_release_exe_url(self.version)
            
            # リクエスト作成
            request = urllib.request.Request(self.download_url)
            request.add_header('User-Agent', f'{APP_NAME}/{APP_VERSION}')
            
            # ダウンロード開始
            with urllib.request.urlopen(request, timeout=30) as response:
                # ファイルサイズ取得
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded_size = 0
                
                # 保存先ディレクトリを作成
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
                
                # ファイルに書き込み
                with open(self.save_path, 'wb') as f:
                    while not self.is_cancelled:
                        chunk = response.read(8192)  # 8KB単位で読み込み
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 進捗計算
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_progress_signal.emit(progress)
                
                if self.is_cancelled:
                    # キャンセルされた場合は一時ファイルを削除
                    if os.path.exists(self.save_path):
                        os.remove(self.save_path)
                    return
                
                # ファイルの整合性チェック（基本的なサイズチェック）
                if total_size > 0 and os.path.getsize(self.save_path) != total_size:
                    raise Exception("ダウンロードファイルのサイズが一致しません")
                
                # ダウンロード完了
                self.download_finished_signal.emit(self.save_path)
                
        except Exception as e:
            self.download_error_signal.emit(str(e))
            # エラー時は一時ファイルを削除
            if os.path.exists(self.save_path):
                os.remove(self.save_path)

class UpdateManager:
    """アップデート管理クラス"""
    
    @staticmethod
    def get_github_release_download_url(version):
        """指定されたバージョンのGitHub Release exeダウンロードURLを生成"""
        return f"https://github.com/EpicJunriel/KIK-ClipItBro/releases/download/{version}/ClipItBro.exe"
    
    @staticmethod
    def get_updater_batch_path():
        """updater.batファイルのパスを取得"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller単一exe環境：実行ファイルと同じディレクトリ
            exe_dir = os.path.dirname(sys.executable)
        else:
            # 開発環境：スクリプトと同じディレクトリ
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(exe_dir, 'updater.bat')
    
    @staticmethod
    def get_updater_exe_path():
        """updater.exeファイルのパスを取得"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller単一exe環境：実行ファイルと同じディレクトリ
            exe_dir = os.path.dirname(sys.executable)
        else:
            # 開発環境：スクリプトと同じディレクトリ
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(exe_dir, 'updater.exe')
    
    @staticmethod
    def check_updater_availability():
        """GUIアップデーター(.exe)またはBATアップデーター(.bat)が利用可能かチェック"""
        updater_exe_path = UpdateManager.get_updater_exe_path()
        updater_bat_path = UpdateManager.get_updater_batch_path()
        return os.path.exists(updater_exe_path) or os.path.exists(updater_bat_path)
        """updater.batファイルが利用可能かチェック"""
        updater_path = UpdateManager.get_updater_batch_path()
        return os.path.exists(updater_path)
    
    @staticmethod
    def execute_update_with_batch(new_exe_path):
        """GUIアップデーター(.exe)またはBATアップデーター(.bat)を使ってアップデートを実行"""
        try:
            # 現在の実行ファイルパスを正しく取得
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller単一exe環境
                current_exe_path = sys.executable
            else:
                # 開発環境
                current_exe_path = os.path.join(os.getcwd(), "ClipItBro.exe")
            
            current_exe_name = os.path.basename(current_exe_path)
            current_exe_dir = os.path.dirname(current_exe_path)
            
            # まずGUIアップデーター(.exe)を試行
            updater_exe_path = UpdateManager.get_updater_exe_path()
            if os.path.exists(updater_exe_path):
                print(f"GUIアップデーターを使用: {updater_exe_path}")
                # GUIアップデーターを実行（引数: 新しいexeパス, 現在のexeファイル名）
                subprocess.Popen(
                    [updater_exe_path, new_exe_path, current_exe_name],
                    cwd=current_exe_dir
                )
                return True
            
            # GUIアップデーターがない場合はBATアップデーターを使用
            updater_bat_path = UpdateManager.get_updater_batch_path()
            if os.path.exists(updater_bat_path):
                print(f"BATアップデーターを使用: {updater_bat_path}")
                # BATアップデーターを実行（引数: 新しいexeパス, 現在のexeファイル名）
                subprocess.Popen(
                    [updater_bat_path, new_exe_path, current_exe_name],
                    cwd=current_exe_dir,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                return True
            
            # どちらも見つからない場合
            raise FileNotFoundError("アップデーター（updater.exe または updater.bat）が見つかりません")
            
        except Exception as e:
            print(f"アップデート実行エラー: {e}")
            return False
    
    @staticmethod
    def create_update_batch(current_exe_path, new_exe_path, restart=True):
        """レガシー: アップデート用バッチファイルを生成（後方互換性のため残す）"""
        current_exe_name = os.path.basename(current_exe_path)
        
        batch_content = f"""@echo off
chcp 65001 > nul
echo ======================================
echo   ClipItBro アップデート中...
echo ======================================
echo.

echo [1/4] 元のプロセス終了を待機中...
:wait_loop
tasklist /FI "IMAGENAME eq {current_exe_name}" 2>NUL | find /I /N "{current_exe_name}">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)
echo ✓ プロセス終了を確認

echo [2/4] バックアップ作成中...
if exist "{current_exe_path}.backup" del "{current_exe_path}.backup"
if exist "{current_exe_path}" (
    move "{current_exe_path}" "{current_exe_path}.backup"
    echo ✓ バックアップ作成完了
) else (
    echo ⚠ 元ファイルが見つかりません
)

echo [3/4] 新しいファイルで置換中...
move "{new_exe_path}" "{current_exe_path}"
if "%ERRORLEVEL%"=="0" (
    echo ✓ ファイル置換完了
) else (
    echo ✗ ファイル置換失敗
    echo 元のファイルを復元しています...
    if exist "{current_exe_path}.backup" move "{current_exe_path}.backup" "{current_exe_path}"
    pause
    exit /b 1
)

echo [4/4] アップデート完了！

echo.
echo ======================================
echo   🎉 アップデート成功！
echo ======================================
"""

        if restart:
            batch_content += f"""
echo 新しいバージョンを起動しています...
start "" "{current_exe_path}"
"""

        batch_content += """
echo 3秒後にこのウィンドウを閉じます...
timeout /t 3 /nobreak >nul

REM 自分自身（バッチファイル）を削除
del "%~f0"
"""
        
        # バッチファイルパス生成
        update_batch_path = os.path.join(
            os.path.dirname(current_exe_path), 
            "clipitbro_update.bat"
        )
        
        # バッチファイル保存
        with open(update_batch_path, 'w', encoding='shift_jis') as f:
            f.write(batch_content)
        
        return update_batch_path
    
    @staticmethod
    def execute_update(current_exe_path, new_exe_path, restart=True):
        """アップデートを実行"""
        try:
            # バッチファイル作成
            batch_path = UpdateManager.create_update_batch(
                current_exe_path, new_exe_path, restart
            )
            
            # バッチファイルを実行
            subprocess.Popen(
                [batch_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True
            )
            
            return True
            
        except Exception as e:
            print(f"アップデート実行エラー: {e}")
            return False

class ThemeManager:
    """テーマ管理クラス"""
    
    LIGHT_THEME = {
        'name': 'Light',
        'main_bg': '#ffffff',
        'text_bg': '#ffffff',
        'text_color': '#000000',
        'border_color': '#cccccc',
        'button_bg': '#007ACC',
        'button_hover': '#005a9e',
        'button_text': '#ffffff',
        'slider_bg': '#f0f0f0',
        'slider_handle': '#007ACC',
        'progress_bg': '#f0f0f0',
        'progress_chunk': '#40e0d0',  # より明るく薄いターコイズグリーン
        'menu_bg': '#ffffff',
        'menu_text': '#000000',
        'log_bg': '#ffffff',
        'log_text': '#333333',
        # 状態別背景色
        'status_success': '#d4fcdc',  # FFmpeg正常（緑）
        'status_error': '#ffd6d6',    # FFmpeg エラー（赤）
        'status_warning': '#fff3cd',  # FFprobe警告（黄）
        'status_active': '#e6f3ff'    # 動画ファイル選択（青）
    }
    
    DARK_THEME = {
        'name': 'Dark',
        'main_bg': '#2b2b2b',
        'text_bg': '#383838',
        'text_color': '#ffffff',
        'border_color': '#555555',
        'button_bg': '#0078d4',
        'button_hover': '#106ebe',
        'button_text': '#ffffff',
        'slider_bg': '#4a4a4a',
        'slider_handle': '#0078d4',
        'progress_bg': '#4a4a4a',
        'progress_chunk': '#20c997',  # ダークテーマ用のさわやかな緑色
        'menu_bg': '#2b2b2b',
        'menu_text': '#ffffff',
        'log_bg': '#383838',
        'log_text': '#ffffff',
        # 状態別背景色（ダークテーマ版）
        'status_success': '#2d5a2d',  # FFmpeg正常（暗い緑）
        'status_error': '#5a2d2d',    # FFmpeg エラー（暗い赤）
        'status_warning': '#5a4f2d',  # FFprobe警告（暗い黄）
        'status_active': '#2d4a5a'    # 動画ファイル選択（暗い青）
    }
    
    @staticmethod
    def get_stylesheet(theme):
        """テーマに基づいてスタイルシートを生成"""
        return f"""
        QMainWindow {{
            background-color: {theme['main_bg']};
            color: {theme['text_color']};
        }}
        
        QTextEdit, DragDropTextEdit {{
            background-color: {theme['text_bg']} !important;
            color: {theme['text_color']} !important;
            border: 1px solid {theme['border_color']} !important;
            border-radius: 4px;
            padding: 8px;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 11px;
        }}
        
        QPushButton {{
            background-color: {theme['button_bg']};
            color: {theme['button_text']};
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {theme['button_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme['button_hover']};
        }}
        
        QPushButton:disabled {{
            background-color: {theme['slider_bg']};
            color: {theme['border_color']};
        }}
        
        QSlider::groove:horizontal {{
            border: 1px solid {theme['border_color']};
            height: 6px;
            background: {theme['slider_bg']};
            margin: 2px 0;
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {theme['slider_handle']};
            border: 2px solid {theme['border_color']};
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
            outline: none;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {theme['button_hover']};
            border: 2px solid {theme['text_color']};
        }}
        
        QSlider::handle:horizontal:pressed {{
            background: {theme['text_color']};
            border: 2px solid {theme['border_color']};
        }}
        
        QSlider::handle:horizontal:disabled {{
            background: {theme['slider_bg']};
            border: 2px solid {theme['border_color']};
        }}
        
        QProgressBar {{
            border: 1px solid {theme['border_color']};
            border-radius: 4px;
            text-align: center;
            background-color: {theme['progress_bg']};
            color: {theme['text_color']};
        }}
        
        QProgressBar::chunk {{
            background-color: {theme['progress_chunk']};
            border-radius: 3px;
        }}
        
        QLabel {{
            color: {theme['text_color']};
            background-color: transparent;
        }}
        
        QLabel#size_estimation {{
            background-color: {theme['text_bg']};
            color: {theme['text_color']};
            padding: 5px;
            border: 1px solid {theme['border_color']};
            border-radius: 3px;
        }}
        
        QWidget {{
            background-color: {theme['main_bg']};
            color: {theme['text_color']};
        }}
        
        QMenuBar {{
            background-color: {theme['menu_bg']};
            color: {theme['menu_text']};
            border-bottom: 1px solid {theme['border_color']};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {theme['button_bg']};
            color: {theme['button_text']};
        }}
        
        QMenu {{
            background-color: {theme['menu_bg']};
            color: {theme['menu_text']};
            border: 1px solid {theme['border_color']};
            padding: 1px;
            font-size: 13px;
        }}
        
        QMenu::item {{
            padding: 2px 8px 2px 2px;
            min-height: 16px;
            background-color: transparent;
            margin: 0px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['button_bg']};
            color: {theme['button_text']};
            border-radius: 2px;
        }}
        
        QMenu::indicator {{
            width: 12px;
            height: 12px;
            left: 2px;
            margin-right: 2px;
        }}
        
        QMenu::indicator:checkable:checked {{
            background-color: transparent;
            border: none;
        }}
        
        QMenu::indicator:checkable:unchecked {{
            background-color: transparent;
            border: none;
            width: 0px;
            height: 0px;
        }}
        
        QMenu::indicator:checkable:checked:selected {{
            background-color: transparent;
            border: none;
        }}
        
        QMenu::indicator:checkable:unchecked:selected {{
            background-color: transparent;
            border: none;
            width: 0px;
            height: 0px;
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {theme['border_color']};
            margin: 3px 6px;
        }}
        
        QDialog {{
            background-color: {theme['main_bg']};
            color: {theme['text_color']};
        }}
        """
    
    @staticmethod
    def apply_theme_to_widget(widget, theme):
        """特定のウィジェットにテーマを強制適用"""
        if hasattr(widget, 'setStyleSheet'):
            if isinstance(widget, QTextEdit):
                # テキストエリア専用の強制スタイル適用
                text_style = f"""
                QTextEdit {{
                    background-color: {theme['text_bg']} !important;
                    color: {theme['text_color']} !important;
                    border: 1px solid {theme['border_color']} !important;
                    border-radius: 4px;
                    padding: 8px;
                    font-family: "Consolas", "Monaco", monospace;
                    font-size: 11px;
                }}
                """
                widget.setStyleSheet(text_style)
            elif isinstance(widget, QLabel) and widget.objectName() == "size_estimation":
                # ファイルサイズ推定ラベル専用
                label_style = f"""
                QLabel {{
                    background-color: {theme['text_bg']} !important;
                    color: {theme['text_color']} !important;
                    padding: 5px;
                    border: 1px solid {theme['border_color']};
                    border-radius: 3px;
                }}
                """
                widget.setStyleSheet(label_style)
            elif isinstance(widget, QPushButton):
                # ボタン専用
                button_style = f"""
                QPushButton {{
                    background-color: {theme['button_bg']} !important;
                    color: {theme['button_text']} !important;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {theme['button_hover']} !important;
                }}
                QPushButton:disabled {{
                    background-color: {theme['slider_bg']} !important;
                    color: {theme['border_color']} !important;
                }}
                """
                widget.setStyleSheet(button_style)
            elif isinstance(widget, QProgressBar):
                # プログレスバー専用
                progress_style = f"""
                QProgressBar {{
                    border: 1px solid {theme['border_color']} !important;
                    border-radius: 4px;
                    text-align: center;
                    background-color: {theme['progress_bg']} !important;
                    color: {theme['text_color']} !important;
                }}
                QProgressBar::chunk {{
                    background-color: {theme['progress_chunk']} !important;
                    border-radius: 3px;
                }}
                """
                widget.setStyleSheet(progress_style)
    
    @staticmethod
    def apply_status_background(text_edit, theme, status):
        """テキストエリアに状態別背景色を適用"""
        status_colors = {
            'success': theme['status_success'],   # FFmpeg正常
            'error': theme['status_error'],       # FFmpeg エラー
            'warning': theme['status_warning'],   # FFprobe警告
            'active': theme['status_active'],     # 動画ファイル選択
            'default': theme['text_bg']           # デフォルト
        }
        
        bg_color = status_colors.get(status, theme['text_bg'])
        
        status_style = f"""
        QTextEdit {{
            background-color: {bg_color} !important;
            color: {theme['text_color']} !important;
            border: 1px solid {theme['border_color']} !important;
            border-radius: 4px;
            padding: 8px;
            font-family: "Consolas", "Monaco", monospace;
            font-size: 11px;
        }}
        """
        text_edit.setStyleSheet(status_style)

class DragDropTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setReadOnly(True)
        self.video_file_path = None  # ドロップされた動画ファイルのパスを保存
        self.original_style = ""  # 元のスタイルを保存
        self.log_messages = []  # ログメッセージを保存
        self.video_info = None  # 動画情報を保存
        self.parent_window = parent  # 親ウィンドウへの参照を保存
        self.first_pass_completed = False  # 1pass目完了フラグ
        self.first_pass_data = None  # 1pass目で生成されたデータ

    def contextMenuEvent(self, event):
        """右クリックコンテキストメニューを表示"""
        context_menu = QMenu(self)
        
        # Aboutアクション
        about_action = QAction('ClipItBro について', self)
        about_action.triggered.connect(self.show_about_from_context)
        context_menu.addAction(about_action)
        
        # セパレーター
        context_menu.addSeparator()
        
        # ログクリアアクション
        clear_action = QAction('ログをクリア', self)
        clear_action.triggered.connect(self.clear_logs)
        context_menu.addAction(clear_action)
        
        # コンテキストメニューを表示
        context_menu.exec_(event.globalPos())
    
    def show_about_from_context(self):
        """コンテキストメニューからAboutダイアログを表示"""
        if self.parent_window and hasattr(self.parent_window, 'show_about_dialog'):
            self.parent_window.show_about_dialog()
        else:
            # 直接Aboutダイアログを作成
            about_dialog = AboutDialog(self)
            about_dialog.exec_()
    
    def clear_logs(self):
        """ログをクリア"""
        self.log_messages.clear()
        self.update_display()

    def add_log(self, message):
        """ログメッセージを追加してテキストエリアに表示"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_messages.append(log_entry)
        print(log_entry)  # コンソールにも出力
        
        # ログが多くなりすぎないよう、最新の15件のみ保持
        if len(self.log_messages) > 15:
            self.log_messages = self.log_messages[-15:]
        
        self.update_display()

    def update_display(self):
        """現在の状態に応じてテキストエリアの内容を更新"""
        if self.video_file_path:
            content = f"動画ファイルが選択されました:\n{self.video_file_path}\n\n"
            
            # 動画情報を表示
            if self.video_info:
                content += "=== 動画情報 ===\n"
                content += f"解像度: {self.video_info.get('width', 'N/A')}x{self.video_info.get('height', 'N/A')}\n"
                content += f"フレームレート: {self.video_info.get('fps', 'N/A')} fps\n"
                content += f"長さ: {self.video_info.get('duration', 'N/A')} 秒\n"
                content += f"ビットレート: {self.video_info.get('bitrate', 'N/A')} kbps\n"
                content += f"ファイルサイズ: {self.video_info.get('file_size', 'N/A')} MB\n"
                
                # 親ウィンドウからエンコード方式を取得
                parent = self.parent()
                while parent and not hasattr(parent, 'encoding_mode'):
                    parent = parent.parent()
                
                # エンコード方式に応じた1pass状態表示
                if parent and parent.encoding_mode == 'twopass':
                    if self.first_pass_completed:
                        content += f"✓ 1pass解析完了: 最適化準備完了\n"
                    elif hasattr(self, '_first_pass_running') and self._first_pass_running:
                        content += f"🔄 1pass解析中...\n"
                    else:
                        content += f"⏳ 1pass解析待機中\n"
                else:
                    content += f"📊 CRF方式選択中 (1pass解析不要)\n"
                content += "\n"
        else:
            content = f"{APP_NAME} v{APP_VERSION} powered by {APP_DEVELOPER}\n"
            content += "動画ファイル（mp4, avi, mov等）をここにドラッグ&ドロップしてください\n"
            content += "2pass方式では、ドロップ時に自動的に1pass解析を実行します\n\n"

        content += "=== ログ ===\n"
        content += "\n".join(self.log_messages)
        
        self.setText(content)

    def get_video_info(self, file_path):
        """FFprobeを使って動画情報を取得"""
        ffprobe_path = get_ffmpeg_executable_path('ffprobe.exe')
        try:
            # ファイルパスを適切に処理（空白を含むパスに対応）
            # Windowsの場合、パスを正規化
            normalized_path = os.path.normpath(file_path)
            
            # FFprobeで動画情報を取得（リスト形式でコマンドを構築することで空白を含むパスに対応）
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                normalized_path  # 正規化されたパスを使用
            ]
            
            # Windows環境での文字エンコーディング問題を解決するため、環境変数を設定
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            if os.name == 'nt':  # Windows環境の場合
                env['LANG'] = 'ja_JP.UTF-8'
            
            # Windowsでコマンドプロンプトウィンドウを表示しないための設定
            kwargs = {
                'capture_output': True, 
                'text': True, 
                'check': True,
                'encoding': 'utf-8', 
                'errors': 'replace', 
                'env': env
            }
            if os.name == 'nt':  # Windows環境の場合
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = startupinfo
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, **kwargs)
            
            # デバッグ用：コマンドと出力を記録
            self.add_log(f"FFprobe実行: {' '.join(cmd[:3])} ... {os.path.basename(normalized_path)}")
            
            if not result.stdout or result.stdout.strip() == "":
                self.add_log(f"FFprobe出力が空です。stderr: {result.stderr}")
                return None
                
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as json_err:
                self.add_log(f"JSON解析エラー: {json_err}")
                self.add_log(f"FFprobe出力の最初の100文字: {result.stdout[:100]}")
                self.add_log(f"FFprobe stderr: {result.stderr}")
                return None
            
            # 動画ストリームを探す
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if video_stream:
                # フレームレートの計算
                fps_str = video_stream.get('r_frame_rate', '0/1')
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    fps = round(num / den, 2) if den != 0 else 0
                else:
                    fps = float(fps_str)
                
                # ファイルサイズの取得
                file_size = round(int(data.get('format', {}).get('size', 0)) / (1024 * 1024), 2)
                
                # ビットレートの取得
                bitrate = data.get('format', {}).get('bit_rate')
                if bitrate:
                    bitrate = round(int(bitrate) / 1000)  # kbpsに変換
                
                info = {
                    'width': video_stream.get('width'),
                    'height': video_stream.get('height'),
                    'fps': fps,
                    'duration': round(float(data.get('format', {}).get('duration', 0)), 2),
                    'bitrate': bitrate,
                    'file_size': file_size,
                    'codec': video_stream.get('codec_name')
                }
                
                self.add_log(f"動画情報を取得: {info['width']}x{info['height']}, {info['fps']}fps, {info['duration']}秒")
                return info
            else:
                self.add_log("動画ストリームが見つかりませんでした")
                return None
                
        except subprocess.CalledProcessError as e:
            self.add_log(f"FFprobe実行エラー: {e}")
            return None
        except json.JSONDecodeError as e:
            self.add_log(f"JSON解析エラー: {e}")
            return None
        except Exception as e:
            self.add_log(f"動画情報取得エラー: {e}")
            return None

    def dragEnterEvent(self, event):
        self.add_log("ドラッグが開始されました")
        
        # FFmpegが利用できない場合はドラッグを拒否
        if hasattr(self, 'parent_window') and self.parent_window and hasattr(self.parent_window, 'ffmpeg_available'):
            if not self.parent_window.ffmpeg_available:
                self.add_log("FFmpegが利用できないため、ドラッグを拒否しました")
                event.ignore()
                return
                
        if event.mimeData().hasUrls():
            urls = [url.toLocalFile() for url in event.mimeData().urls()]
            self.add_log(f"ファイルを検出: {', '.join([os.path.basename(url) for url in urls])}")
            # 元のスタイルを保存
            self.original_style = self.styleSheet()
            # ドラッグ中のスタイルを設定（境界線を追加）
            self.setStyleSheet(self.original_style + "border: 2px dashed #007acc;")
            # 全てのドロップアクションを受け入れ
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self.add_log("ドラッグイベント受け入れ完了")
            return
        event.ignore()
        self.add_log("ドラッグイベント無視")

    def dragMoveEvent(self, event):
        # dragMoveEventも追加してみる
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        event.ignore()

    def dragOverEvent(self, event):
        # FFmpegが利用できない場合はドラッグを拒否
        if hasattr(self, 'parent_window') and self.parent_window and hasattr(self.parent_window, 'ffmpeg_available'):
            if not self.parent_window.ffmpeg_available:
                event.ignore()
                return
                
        if event.mimeData().hasUrls():
            # ドラッグ中のカーソル表示を適切に設定
            event.setDropAction(Qt.CopyAction)
            event.accept()
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        # ドラッグが離れた時に元のスタイルに戻す
        self.add_log("ドラッグが離脱しました")
        self.setStyleSheet(self.original_style)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.add_log("=== ドロップイベント開始 ===")
        
        # FFmpegが利用できない場合はドロップを拒否
        if hasattr(self, 'parent_window') and self.parent_window and hasattr(self.parent_window, 'ffmpeg_available'):
            if not self.parent_window.ffmpeg_available:
                self.add_log("FFmpegが利用できないため、ファイルドロップを拒否しました")
                event.ignore()
                return
        
        # まず境界線スタイルを元に戻す
        if hasattr(self, 'original_style'):
            self.setStyleSheet(self.original_style)
        
        # MimeDataの確認
        if not event.mimeData():
            self.add_log("MimeDataが存在しません")
            event.ignore()
            return
            
        if not event.mimeData().hasUrls():
            self.add_log("URLが存在しません")
            event.ignore()
            return
            
        urls = event.mimeData().urls()
        self.add_log(f"URL数: {len(urls)}")
        
        for i, url in enumerate(urls):
            file_path = url.toLocalFile()
            self.add_log(f"URL[{i}]: {file_path}")
            
            if not file_path:
                self.add_log(f"URL[{i}]: ローカルファイルパスが空です")
                continue
            
            # ファイルパスを正規化（空白や特殊文字を含むパスに対応）
            try:
                normalized_path = os.path.normpath(file_path)
                # パスの存在確認は正規化されたパスで行う
                if not os.path.exists(normalized_path):
                    self.add_log(f"ファイルが存在しません: {normalized_path}")
                    continue
                    
                self.add_log(f"ファイル存在確認OK: {os.path.basename(normalized_path)}")
                
                if self.is_video_file(normalized_path):
                    self.add_log(f"動画ファイル判定OK: {os.path.basename(normalized_path)}")
                    
                    # 新しい動画ファイルの場合、1pass解析状態をリセット
                    if self.video_file_path != normalized_path:
                        self.add_log("新しい動画ファイルを検出 - 1pass解析をリセット")
                        self.first_pass_completed = False
                        self.first_pass_data = None
                        if hasattr(self, 'first_pass_codec'):
                            self.first_pass_codec = None
                        if hasattr(self, '_first_pass_running'):
                            self._first_pass_running = False
                        
                        # 親ウィンドウのプログレスバーをリセット
                        parent = self.parent()
                        while parent and not hasattr(parent, 'pass1_progress_bar'):
                            parent = parent.parent()
                        if parent:
                            parent.pass1_progress_bar.setValue(0)
                            parent.pass2_progress_bar.setValue(0)
                    
                    # 動画ファイルとして処理（正規化されたパスを使用）
                    self.video_file_path = normalized_path
                    
                    # 親ウィンドウのテーマを取得して青い背景を適用
                    if self.parent_window and hasattr(self.parent_window, 'current_theme'):
                        self.parent_window.current_status = 'active'
                        ThemeManager.apply_status_background(self, self.parent_window.current_theme, 'active')
                    else:
                        self.setStyleSheet('background-color: #e6f3ff;')  # フォールバック
                    
                    self.add_log(f"動画ファイルとして設定完了: {os.path.basename(normalized_path)}")
                    
                    # 動画情報を取得
                    self.add_log("動画情報取得を開始...")
                    self.video_info = self.get_video_info(normalized_path)
                    
                    if self.video_info:
                        self.add_log("動画情報取得成功")
                        self.trigger_size_estimation()
                    else:
                        self.add_log("動画情報取得失敗")
                    
                    # イベントを受け入れ
                    event.setDropAction(Qt.CopyAction)
                    event.accept()
                    self.add_log("=== ドロップイベント正常終了 ===")
                    return
                    
                else:
                    self.add_log(f"動画ファイルではありません: {os.path.basename(normalized_path)}")
                    # 親ウィンドウのテーマを取得して黄色い背景を適用
                    if self.parent_window and hasattr(self.parent_window, 'current_theme'):
                        ThemeManager.apply_status_background(self, self.parent_window.current_theme, 'warning')
                    else:
                        self.setStyleSheet('background-color: #fff3cd;')  # フォールバック
                    event.setDropAction(Qt.CopyAction)
                    event.accept()
                    self.add_log("=== ドロップイベント終了（非動画ファイル） ===")
                    return
                    
            except Exception as e:
                self.add_log(f"ファイルパス処理エラー: {e}")
                continue
        
        self.add_log("=== ドロップイベント無視 ===")
        event.ignore()

    def insertFromMimeData(self, source):
        """QTextEditの標準的なドロップ処理もオーバーライド"""
        self.add_log("insertFromMimeData が呼ばれました")
        if source.hasUrls():
            urls = source.urls()
            self.add_log(f"insertFromMimeData でURL検出: {len(urls)}件")
            for url in urls:
                file_path = url.toLocalFile()
                self.add_log(f"insertFromMimeData: {file_path}")
                if file_path:
                    try:
                        # ファイルパスを正規化
                        normalized_path = os.path.normpath(file_path)
                        if os.path.exists(normalized_path) and self.is_video_file(normalized_path):
                            # 新しい動画ファイルの場合、1pass解析状態をリセット
                            if self.video_file_path != normalized_path:
                                self.add_log("新しい動画ファイルを検出 - 1pass解析をリセット")
                                self.first_pass_completed = False
                                self.first_pass_data = None
                                if hasattr(self, 'first_pass_codec'):
                                    self.first_pass_codec = None
                                if hasattr(self, '_first_pass_running'):
                                    self._first_pass_running = False
                                
                                # 親ウィンドウのプログレスバーをリセット
                                parent = self.parent()
                                while parent and not hasattr(parent, 'pass1_progress_bar'):
                                    parent = parent.parent()
                                if parent:
                                    parent.pass1_progress_bar.setValue(0)
                                    parent.pass2_progress_bar.setValue(0)
                            
                            self.video_file_path = normalized_path
                            self.video_info = self.get_video_info(normalized_path)
                            if self.video_info:
                                self.trigger_size_estimation()
                    except Exception as e:
                        self.add_log(f"insertFromMimeData パス処理エラー: {e}")
            return
        # 通常のテキストドロップは無視
        pass

    def trigger_size_estimation(self):
        """親ウィンドウのファイルサイズ推定を実行"""
        try:
            # より確実に親ウィンドウを取得
            parent = self.parent()
            while parent and not hasattr(parent, 'update_size_estimation'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'update_size_estimation'):
                self.add_log("ファイルサイズ推定を実行中...")
                # エンコード方式に応じて適切な推定メソッドを呼ぶ
                if hasattr(parent, 'encoding_mode'):
                    if parent.encoding_mode == 'twopass':
                        parent.update_bitrate_estimation()
                    else:
                        parent.update_size_estimation()
                else:
                    # デフォルトは2pass方式
                    parent.update_bitrate_estimation()
                self.add_log("ファイルサイズ推定完了")
                # 変換ボタンを有効化
                if hasattr(parent, 'convert_button'):
                    parent.convert_button.setEnabled(True)
                    self.add_log("変換ボタンを有効化しました")
                    
                # 1pass目を自動実行
                self.start_first_pass()
            else:
                self.add_log("MainWindowが見つかりません - 直接検索を試行")
                # QApplicationから全てのウィジェットを検索
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'update_size_estimation') and hasattr(widget, 'text_edit'):
                            self.add_log("MainWindowを発見 - 推定実行")
                            # エンコード方式に応じて適切な推定メソッドを呼ぶ
                            if hasattr(widget, 'encoding_mode'):
                                if widget.encoding_mode == 'twopass':
                                    widget.update_bitrate_estimation()
                                else:
                                    widget.update_size_estimation()
                            else:
                                # デフォルトは2pass方式
                                widget.update_bitrate_estimation()
                            if hasattr(widget, 'convert_button'):
                                widget.convert_button.setEnabled(True)
                                self.add_log("変換ボタンを有効化しました")
                            self.add_log("ファイルサイズ推定完了")
                            # 1pass目を自動実行
                            self.start_first_pass()
                            return
                self.add_log("MainWindowが見つかりませんでした")
        except Exception as e:
            self.add_log(f"ファイルサイズ推定エラー: {e}")

    def start_first_pass(self):
        """1pass目の解析を開始"""
        if not self.video_file_path:
            self.add_log("動画ファイルが選択されていないため、1pass解析をスキップ")
            return
            
        if self.first_pass_completed:
            self.add_log("1pass解析は既に完了済みです")
            return
            
        if hasattr(self, '_first_pass_running') and self._first_pass_running:
            self.add_log("1pass解析は既に実行中です - 重複実行を防止")
            return
            
        # 親ウィンドウに実行中のスレッドがないか確認
        parent = self.parent()
        while parent and not hasattr(parent, 'first_pass_thread'):
            parent = parent.parent()
        if parent and hasattr(parent, 'first_pass_thread') and parent.first_pass_thread and parent.first_pass_thread.isRunning():
            self.add_log("既に1pass解析が実行中です - 重複実行を防止")
            return
            
        try:
            self.add_log("=== 1pass解析開始 ===")
            self._first_pass_running = True
            self.update_display()
            
            # 親ウィンドウからエンコード方式を取得
            parent = self.parent()
            while parent and not hasattr(parent, 'encoding_mode'):
                parent = parent.parent()
                
            if not parent:
                self.add_log("親ウィンドウが見つかりません - 1pass解析をスキップ")
                self._first_pass_running = False
                return
                
            # 2pass方式の場合のみ1pass目を実行
            if parent.encoding_mode == 'twopass':
                # 実行ボタンを無効化し、2passプログレスバーを表示
                parent.convert_button.setEnabled(False)
                parent.convert_button.setText('1pass解析中...')
                parent.twopass_progress_widget.setVisible(True)
                parent.pass1_progress_bar.setValue(0)
                parent.pass2_progress_bar.setValue(0)
                
                # デフォルトのビットレートで1pass目を実行（後で調整される）
                temp_bitrate = 1000  # 仮のビットレート
                
                # 動画の総時間を取得
                total_duration = 0
                if self.video_info:
                    total_duration = self.video_info.get('duration', 0)
                
                # 1pass目用のスレッドを作成
                from PyQt5.QtCore import QThread, pyqtSignal
                use_h265 = parent.use_h265_encoding if hasattr(parent, 'use_h265_encoding') else False
                self.first_pass_thread = FirstPassThread(self.video_file_path, temp_bitrate, total_duration, use_h265)
                self.first_pass_thread.log_signal.connect(self.add_log)
                self.first_pass_thread.progress_signal.connect(parent.update_first_pass_progress)
                self.first_pass_thread.finished_signal.connect(self.first_pass_finished)
                self.first_pass_thread.start()
            else:
                self.add_log("CRF方式が選択されているため、1pass解析をスキップします")
                self._first_pass_running = False
                
        except Exception as e:
            self.add_log(f"1pass解析開始エラー: {e}")
            self._first_pass_running = False
            self.update_display()

    def first_pass_finished(self, success, log_file_path, error_message):
        """1pass目完了時の処理"""
        self._first_pass_running = False
        
        # 親ウィンドウを取得
        parent = self.parent()
        while parent and not hasattr(parent, 'convert_button'):
            parent = parent.parent()
        
        if success:
            self.first_pass_completed = True
            self.first_pass_data = log_file_path
            
            # 1passで使用したコーデック情報を記録
            use_h265 = parent.use_h265_encoding if hasattr(parent, 'use_h265_encoding') else False
            self.first_pass_codec = 'H.265' if use_h265 else 'H.264'
            
            self.add_log("=== 1pass解析完了 ===")
            self.add_log(f"📹 解析時のコーデック: {self.first_pass_codec}")
            self.add_log("2pass変換の準備が整いました")
            
            # 親ウィンドウのテーマを取得して緑い背景を適用（解析完了）
            if self.parent_window and hasattr(self.parent_window, 'current_theme'):
                ThemeManager.apply_status_background(self, self.parent_window.current_theme, 'success')
            
            # 実行ボタンを有効化（1pass完了で2pass実行可能）
            if parent:
                parent.convert_button.setEnabled(True)
                parent.convert_button.setText('変換実行 (2pass)')
                # 1pass目のプログレスバーを100%で固定
                parent.pass1_progress_bar.setValue(100)
                # 2pass目は0%のまま（ユーザーのボタン押下待ち）
                parent.pass2_progress_bar.setValue(0)
            
        else:
            self.add_log("=== 1pass解析失敗 ===")
            if error_message:
                self.add_log(f"1passエラー: {error_message}")
            
            # 警告背景を適用
            if self.parent_window and hasattr(self.parent_window, 'current_theme'):
                ThemeManager.apply_status_background(self, self.parent_window.current_theme, 'warning')
            
            # 実行ボタンを有効化（エラーでも再試行可能にする）
            if parent:
                parent.convert_button.setEnabled(True)
                parent.convert_button.setText('変換実行 (2pass)')
                # エラー時はプログレスバーを非表示
                parent.twopass_progress_widget.setVisible(False)
        
        self.update_display()

    def is_video_file(self, file_path):
        """ファイルが動画ファイルかどうかを拡張子で判定"""
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp']
        return any(file_path.lower().endswith(ext) for ext in video_extensions)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Windows固有の設定を最初に実行（タスクバー統合のため）
        self.setup_windows_taskbar_integration()
        
        # MainWindowのドラッグアンドドロップは無効にして、子ウィジェットで処理
        # self.setAcceptDrops(False) を削除
        self.setWindowTitle('ClipItBro')  # シンプルなタイトル（タスクバー統合のため）
        self.setGeometry(100, 100, 700, 600)  # サイズを大きくする

        # タスクバープログレス機能を初期化
        self.taskbar_progress = TaskbarProgress(self)

        # 設定管理
        self.settings = QSettings('ClipItBro', 'ClipItBro')
        
        # テーマ初期化
        self.current_theme = ThemeManager.LIGHT_THEME
        self.load_theme_setting()
        
        # 自動クリップボードコピー設定を読み込み
        self.auto_clipboard_copy = self.settings.value('auto_clipboard_copy', False, type=bool)
        
        # H.265エンコード設定を読み込み（試験的機能）
        self.use_h265_encoding = self.settings.value('use_h265_encoding', False, type=bool)
        
        # 状態管理（テーマ変更時の背景色復元用）
        self.current_status = 'default'  # default, success, error, warning, active
        self.ffmpeg_available = False  # FFmpeg利用可能フラグ
        
        # エンコード方式管理
        self.encoding_mode = 'twopass'  # 'twopass' または 'crf'

        # アップデート確認機能
        self.update_available = False  # アップデートが利用可能かどうか
        self.latest_version = None     # 最新バージョン
        self.is_unreleased_version = False  # 未公開バージョンかどうか
        self.released_version = None   # リリース版のバージョン
        self.update_menu_action = None # アップデートメニューアクション

        # メニューバーを作成
        self.create_menu_bar()

        # メインウィジェットとレイアウト
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)

        # テキストエリアコンテナ（警告バー含む）
        self.text_area_container = QWidget()
        text_container_layout = QVBoxLayout(self.text_area_container)
        text_container_layout.setContentsMargins(0, 0, 0, 0)
        text_container_layout.setSpacing(0)

        # ffmpeg情報表示エリア（ドラッグ＆ドロップ対応）
        self.text_edit = DragDropTextEdit(self)
        text_container_layout.addWidget(self.text_edit)

        # H.265警告バー（初期は非表示）
        self.h265_warning_bar = QLabel()
        self.h265_warning_bar.setText("⚠️ H.265 エンコーディング（試験的機能）が有効です - 一部デバイスで再生できない場合があります")
        self.h265_warning_bar.setAlignment(Qt.AlignCenter)
        self.h265_warning_bar.setStyleSheet("""
            QLabel {
                background-color: #ffebee;
                color: #c62828;
                border: 1px solid #ef5350;
                padding: 4px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        self.h265_warning_bar.setFixedHeight(24)
        self.h265_warning_bar.setVisible(False)  # 初期は非表示
        text_container_layout.addWidget(self.h265_warning_bar)

        main_layout.addWidget(self.text_area_container)

        # パラメータ入力欄（画面下部に固定）
        param_widget = QWidget(self)
        param_layout = QVBoxLayout(param_widget)

        # パラメータ入力欄
        param_input_layout = QHBoxLayout()

        # エンコード方式切り替えボタン（一番左に配置）
        self.mode_button = QPushButton('2pass', self)
        self.mode_button.clicked.connect(self.toggle_encoding_mode)
        self.mode_button.setFixedWidth(80)  # ボタンの幅を固定
        param_input_layout.addWidget(self.mode_button)

        # 2pass方式用：ファイルサイズ入力
        self.size_input_widget = QWidget()
        size_layout = QHBoxLayout(self.size_input_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        
        size_label = QLabel('目標ファイルサイズ (MB):', self)
        self.size_slider = QSlider(Qt.Horizontal, self)
        self.size_slider.setRange(1, 100)  # 1MB～100MB
        self.size_slider.setValue(9)  # デフォルト9MB
        self.size_value_label = QLabel(str(self.size_slider.value()), self)
        self.size_slider.valueChanged.connect(lambda v: (
            self.size_value_label.setText(str(v)),
            self.update_bitrate_estimation()
        ))
        
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_value_label)
        size_layout.addWidget(QLabel('MB', self))

        # CRF方式用：従来のスライダー（非表示状態で作成）
        self.crf_input_widget = QWidget()
        crf_layout = QHBoxLayout(self.crf_input_widget)
        crf_layout.setContentsMargins(0, 0, 0, 0)
        
        # CRFスライダー
        crf_label = QLabel('CRF:', self)
        self.crf_slider = QSlider(Qt.Horizontal, self)
        self.crf_slider.setRange(1, 50)
        self.crf_slider.setValue(28)
        self.crf_slider.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.crf_slider.setAttribute(Qt.WA_NoSystemBackground, False)
        self.crf_value_label = QLabel(str(self.crf_slider.value()), self)
        self.crf_slider.valueChanged.connect(lambda v: (
            self.crf_value_label.setText(str(v)),
            self.update_size_estimation() if self.encoding_mode == 'crf' else None
        ))
        
        # vfスライダー（0.1～1.0を1～10で扱う）
        vf_label = QLabel('vf:', self)
        self.vf_slider = QSlider(Qt.Horizontal, self)
        self.vf_slider.setRange(1, 10)
        self.vf_slider.setValue(8)
        self.vf_slider.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.vf_slider.setAttribute(Qt.WA_NoSystemBackground, False)
        self.vf_value_label = QLabel(str(self.vf_slider.value() / 10), self)
        self.vf_slider.valueChanged.connect(lambda v: (
            self.vf_value_label.setText(str(v / 10)),
            self.update_size_estimation() if self.encoding_mode == 'crf' else None
        ))
        
        crf_layout.addWidget(crf_label)
        crf_layout.addWidget(self.crf_slider)
        crf_layout.addWidget(self.crf_value_label)
        crf_layout.addWidget(vf_label)
        crf_layout.addWidget(self.vf_slider)
        crf_layout.addWidget(self.vf_value_label)

        # 最初は2pass方式を表示
        param_input_layout.addWidget(self.size_input_widget)
        param_input_layout.addWidget(self.crf_input_widget)
        self.crf_input_widget.setVisible(False)

        param_layout.addLayout(param_input_layout)

        # 情報表示ラベル
        self.info_label = QLabel('目標ファイルサイズ: 9 MB | 推定ビットレート: 動画を選択してください', self)
        self.info_label.setObjectName("size_estimation")
        param_layout.addWidget(self.info_label)

        # 実行ボタン
        self.convert_button = QPushButton('変換実行 (2pass)', self)
        self.convert_button.setEnabled(False)  # 最初は無効（動画選択まで）
        self.convert_button.clicked.connect(self.start_conversion)
        param_layout.addWidget(self.convert_button)

        # プログレスバーエリア
        progress_widget = QWidget(self)
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)

        # 単一プログレスバー（CRF方式用）
        self.single_progress_bar = QProgressBar(self)
        self.single_progress_bar.setVisible(False)
        progress_layout.addWidget(self.single_progress_bar)

        # 2passプログレスバー（横並び）
        self.twopass_progress_widget = QWidget(self)
        twopass_progress_layout = QHBoxLayout(self.twopass_progress_widget)
        twopass_progress_layout.setContentsMargins(0, 0, 0, 0)
        twopass_progress_layout.setSpacing(10)

        # 1pass目プログレスバー
        pass1_container = QWidget()
        pass1_layout = QVBoxLayout(pass1_container)
        pass1_layout.setContentsMargins(0, 0, 0, 0)
        pass1_layout.setSpacing(2)
        
        self.pass1_progress_bar = QProgressBar(self)
        self.pass1_progress_bar.setMinimumHeight(20)
        
        pass1_layout.addWidget(self.pass1_progress_bar)

        # 矢印ラベル
        self.arrow_label = QLabel('>>>', self)
        self.arrow_label.setAlignment(Qt.AlignCenter)
        self.arrow_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #666666;")
        self.arrow_label.setFixedWidth(30)

        # 2pass目プログレスバー
        pass2_container = QWidget()
        pass2_layout = QVBoxLayout(pass2_container)
        pass2_layout.setContentsMargins(0, 0, 0, 0)
        pass2_layout.setSpacing(2)
        
        self.pass2_progress_bar = QProgressBar(self)
        self.pass2_progress_bar.setMinimumHeight(20)
        
        pass2_layout.addWidget(self.pass2_progress_bar)

        # 横並びレイアウトに追加
        twopass_progress_layout.addWidget(pass1_container)
        twopass_progress_layout.addWidget(self.arrow_label)
        twopass_progress_layout.addWidget(pass2_container)
        
        # 2passプログレスバーを最初は非表示
        self.twopass_progress_widget.setVisible(False)
        progress_layout.addWidget(self.twopass_progress_widget)

        param_layout.addWidget(progress_widget)

        main_layout.addWidget(param_widget)
        main_layout.setStretch(0, 1)  # テキストエリアを伸ばす
        main_layout.setStretch(1, 0)  # パラメータ欄は固定

        self.setCentralWidget(central_widget)

        # アプリケーションアイコンを設定（text_edit作成後）
        self.set_application_icon()
        
        # テーマを適用（すべてのウィジェット作成後）
        self.apply_theme()
        
        # システムトレイアイコンを初期化（通知機能用）
        self.init_system_tray()
        
        # FFmpeg バージョン表示（テーマ適用後）
        self.show_ffmpeg_version()
        
        # H.265警告バーの初期状態を設定
        self.update_h265_warning_bar()
        
        # アップデート確認を開始（2秒後に実行）
        QTimer.singleShot(2000, self.start_update_check)

    def setup_windows_taskbar_integration(self):
        """Windowsタスクバー統合の設定（テスト用に無効化）"""
        # updater.exeでは動作するため、このコードが原因の可能性
        # 一旦無効化してテスト
        print("Windows統合コード: 無効化中（テスト）")
        pass

    def ensure_taskbar_integration(self):
        """ウィンドウ作成後のタスクバー統合確認（テスト用に無効化）"""
        # 一旦無効化してテスト
        print("タスクバー統合確認: 無効化中（テスト）")
        pass

    def set_application_icon(self):
        # EXE環境でのリソースパス取得
        def get_resource_path(relative_path):
            """EXE環境とスクリプト環境の両方でリソースパスを取得"""
            if hasattr(sys, '_MEIPASS'):
                # PyInstallerでパッケージ化された環境
                return os.path.join(sys._MEIPASS, relative_path)
            else:
                # 通常のPythonスクリプト環境
                return relative_path
        
        # カスタムアイコンファイルを検索（複数の形式をサポート）
        icon_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif']
        custom_icon_path = None
        
        # app.icoを優先的に検索（Windowsの標準）
        priority_paths = ['icon/app.ico', 'app.ico']
        for path in priority_paths:
            resource_path = get_resource_path(path)
            if os.path.exists(resource_path):
                custom_icon_path = resource_path
                break
        
        # .icoが見つからない場合は他の形式を検索
        if not custom_icon_path:
            for ext in icon_extensions[1:]:  # .ico以外
                potential_path = f"icon/app{ext}"
                resource_path = get_resource_path(potential_path)
                if os.path.exists(resource_path):
                    custom_icon_path = resource_path
                    break
        
        if custom_icon_path:
            try:
                # カスタムアイコンを設定
                app_icon = QIcon(custom_icon_path)
                
                # ウィンドウアイコンを設定
                self.setWindowIcon(app_icon)
                
                # アプリケーション全体のアイコンも設定
                QApplication.instance().setWindowIcon(app_icon)
                
                # タスクバーアイコンを確実に設定（Windows固有）
                if sys.platform == "win32":
                    try:
                        import ctypes
                        # アプリケーションユーザーモデルIDを設定してタスクバーアイコンを独立させる
                        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{APP_NAME}.{APP_DEVELOPER}.動画変換")
                    except Exception as e:
                        self.text_edit.add_log(f"タスクバーアイコン設定警告: {e}")
                
                self.text_edit.add_log(f"アプリケーションアイコンを設定しました: {os.path.basename(custom_icon_path)}")
            except Exception as e:
                self.text_edit.add_log(f"アプリケーションアイコン設定エラー: {e}")
                # フォールバック：デフォルトアイコンを設定
                self.set_default_icon()
        else:
            self.text_edit.add_log("カスタムアプリケーションアイコンが見つかりません")
            # フォールバック：デフォルトアイコンを設定
            self.set_default_icon()
    
    def set_default_icon(self):
        """デフォルトアイコンを設定"""
        try:
            # PyQt5の標準アイコンを使用
            style = self.style()
            default_icon = style.standardIcon(style.SP_ComputerIcon)
            self.setWindowIcon(default_icon)
            QApplication.instance().setWindowIcon(default_icon)
            self.text_edit.add_log("デフォルトアイコンを設定しました")
        except Exception as e:
            self.text_edit.add_log(f"デフォルトアイコン設定エラー: {e}")

    def stop_all_running_processes(self):
        """実行中の全プロセスを停止"""
        try:
            # 1pass解析スレッドを停止
            if hasattr(self, 'first_pass_thread') and self.first_pass_thread and self.first_pass_thread.isRunning():
                self.text_edit.add_log("実行中の1pass解析を停止中...")
                self.first_pass_thread.stop()  # カスタムstopメソッドを使用
                
                # 強制的にプロセスを終了
                if hasattr(self.first_pass_thread, 'process') and self.first_pass_thread.process:
                    try:
                        self.first_pass_thread.process.kill()
                    except:
                        pass
                
                if not self.first_pass_thread.wait(1000):  # 1秒待機
                    self.first_pass_thread.terminate()
                    self.first_pass_thread.wait(1000)
                self.first_pass_thread = None
                
            # 実行中フラグを強制リセット
            if hasattr(self.text_edit, '_first_pass_running'):
                self.text_edit._first_pass_running = False
                
            # 2pass変換スレッドを停止
            if hasattr(self, 'twopass_thread') and self.twopass_thread and self.twopass_thread.isRunning():
                self.text_edit.add_log("実行中の2pass変換を停止中...")
                self.twopass_thread.terminate()
                if not self.twopass_thread.wait(3000):  # 3秒待機
                    self.twopass_thread.kill()  # 強制終了
                self.twopass_thread = None
                
            # CRF変換スレッドを停止
            if hasattr(self, 'conversion_thread') and self.conversion_thread and self.conversion_thread.isRunning():
                self.text_edit.add_log("実行中のCRF変換を停止中...")
                self.conversion_thread.terminate()
                if not self.conversion_thread.wait(3000):  # 3秒待機
                    self.conversion_thread.kill()  # 強制終了
                self.conversion_thread = None
                
            # プログレスバーをリセット
            self.pass1_progress_bar.setValue(0)
            self.pass2_progress_bar.setValue(0)
            self.single_progress_bar.setValue(0)
            
            # UIを初期状態に戻す
            self.convert_button.setEnabled(True)
            if self.encoding_mode == 'twopass':
                self.convert_button.setText('変換実行 (2pass)')
            else:
                self.convert_button.setText('変換実行 (CRF)')
                
            # 実行中フラグをリセット
            if hasattr(self.text_edit, '_first_pass_running'):
                self.text_edit._first_pass_running = False
                
        except Exception as e:
            self.text_edit.add_log(f"プロセス停止エラー: {e}")

    def toggle_encoding_mode(self):
        """エンコード方式を切り替え"""
        # ボタンを一時的に無効化（連打防止）
        self.mode_button.setEnabled(False)
        
        # 実行中のスレッドがあれば停止
        self.stop_all_running_processes()
        
        if self.encoding_mode == 'twopass':
            # CRF方式に切り替え
            self.encoding_mode = 'crf'
            self.mode_button.setText('CRF')
            self.convert_button.setText('変換実行 (CRF)')
            
            # UIを切り替え
            self.size_input_widget.setVisible(False)
            self.crf_input_widget.setVisible(True)
            
            # プログレスバーを切り替え（CRF方式では単一バー）
            self.twopass_progress_widget.setVisible(False)
            self.single_progress_bar.setVisible(False)  # 最初は非表示
            
            # 1pass目をリセット（CRF方式では不要）
            if hasattr(self.text_edit, 'first_pass_completed'):
                self.text_edit.first_pass_completed = False
                self.text_edit.first_pass_data = None
                if hasattr(self.text_edit, 'first_pass_codec'):
                    self.text_edit.first_pass_codec = None
                if hasattr(self.text_edit, '_first_pass_running'):
                    self.text_edit._first_pass_running = False
                
                # プログレスバーを0%にリセット
                self.pass1_progress_bar.setValue(0)
                self.pass2_progress_bar.setValue(0)
                
                self.text_edit.add_log("CRF方式に切り替え - 1pass解析をリセット")
            
            # CRF方式では動画があれば実行ボタンを有効化
            if self.text_edit.video_file_path:
                self.convert_button.setEnabled(True)
            
            # 推定を更新
            self.update_size_estimation()
            
        else:
            # 2pass方式に切り替え
            self.encoding_mode = 'twopass'
            self.mode_button.setText('2pass')
            self.convert_button.setText('変換実行 (2pass)')
            
            # UIを切り替え
            self.crf_input_widget.setVisible(False)
            self.size_input_widget.setVisible(True)
            
            # プログレスバーを切り替え（2pass方式では2つのバー）
            self.single_progress_bar.setVisible(False)
            self.twopass_progress_widget.setVisible(False)  # 最初は非表示
            
            # プログレスバーをリセット
            self.pass1_progress_bar.setValue(0)
            self.pass2_progress_bar.setValue(0)
            
            # 1pass解析をリセット（2pass方式では必要）
            if hasattr(self.text_edit, 'first_pass_completed'):
                self.text_edit.first_pass_completed = False
                self.text_edit.first_pass_data = None
                if hasattr(self.text_edit, 'first_pass_codec'):
                    self.text_edit.first_pass_codec = None
                if hasattr(self.text_edit, '_first_pass_running'):
                    self.text_edit._first_pass_running = False
                self.text_edit.add_log("2pass方式に切り替え - 1pass解析をリセット")
            
            # 2pass方式では1pass完了まで実行ボタンを無効化
            self.convert_button.setEnabled(False)
            
            # ビットレート推定を更新
            self.update_bitrate_estimation()
            
            # 動画が選択済みなら1pass目を自動実行（少し遅延させて停止処理を確実にする）
            if self.text_edit.video_file_path:
                self.text_edit.add_log("2pass方式のため1pass解析を開始します")
                # 遅延実行でstop処理を確実にする
                QTimer.singleShot(200, lambda: self.text_edit.start_first_pass())
        
        # ボタンを少し遅延して再有効化（連打防止）
        QTimer.singleShot(500, lambda: self.mode_button.setEnabled(True))

    def calculate_target_bitrate(self, target_size_mb, duration_seconds, audio_bitrate_kbps=128):
        """目標ファイルサイズから必要なビットレートを計算"""
        if duration_seconds <= 0:
            return None
            
        # ビット単位でのファイルサイズ
        target_size_bits = target_size_mb * 8 * 1024 * 1024
        
        # 全体のビットレート（kbps）
        total_bitrate = (target_size_bits / duration_seconds) / 1000
        
        # 音声ビットレートを差し引いて動画ビットレートを計算
        video_bitrate = total_bitrate - audio_bitrate_kbps
        
        # 最小値を保証（100kbps）
        return max(100, int(video_bitrate))

    def update_bitrate_estimation(self):
        """2pass方式でのビットレート推定を更新"""
        if self.encoding_mode != 'twopass':
            return
            
        video_info = self.text_edit.video_info
        target_size = self.size_slider.value()
        
        if not video_info:
            self.info_label.setText(f'目標ファイルサイズ: {target_size} MB | 推定ビットレート: 動画を選択してください')
            return
        
        duration = video_info.get('duration', 0)
        if duration <= 0:
            self.info_label.setText(f'目標ファイルサイズ: {target_size} MB | 推定ビットレート: 動画長不明')
            return
        
        target_bitrate = self.calculate_target_bitrate(target_size, duration)
        
        if target_bitrate:
            # 元ファイルサイズとの比較
            original_size = video_info.get('file_size', 0)
            original_bitrate = video_info.get('bitrate', 0)
            
            text = f'目標ファイルサイズ: {target_size} MB | 推定ビットレート: {target_bitrate} kbps'
            
            if original_size > 0:
                size_ratio = target_size / original_size
                if size_ratio < 1:
                    compression_rate = (1 - size_ratio) * 100
                    text += f' | 圧縮率: {compression_rate:.1f}% 削減'
                else:
                    increase_rate = (size_ratio - 1) * 100
                    text += f' | サイズ増加: {increase_rate:.1f}%'
            
            if original_bitrate > 0:
                bitrate_ratio = target_bitrate / original_bitrate
                text += f' | 元ビットレート: {original_bitrate} kbps ({bitrate_ratio:.2f}x)'
            
            self.info_label.setText(text)
        else:
            self.info_label.setText(f'目標ファイルサイズ: {target_size} MB | ビットレート計算エラー')

    def update_size_estimation(self):
        """CRF方式でのファイルサイズ推定を更新"""
        if self.encoding_mode != 'crf':
            return
            
        print("update_size_estimation called")  # デバッグ用
        
        video_info = self.text_edit.video_info
        if not video_info:
            self.info_label.setText('ファイルサイズ推定: 動画ファイルを選択してください')
            print("No video info available")  # デバッグ用
            return
        
        crf = self.crf_slider.value()
        scale_factor = self.vf_slider.value() / 10.0
        
        print(f"Calculating with CRF={crf}, scale={scale_factor}")  # デバッグ用
        
        estimation = self.estimate_file_size(video_info, crf, scale_factor)
        
        if estimation:
            original_size = video_info.get('file_size', 0)
            
            text = f"ファイルサイズ推定: {estimation['size_mb']} MB "
            text += f"(元: {original_size} MB) "
            text += f"解像度: {estimation['new_resolution']} "
            text += f"推定ビットレート: {estimation['bitrate']} kbps"
            
            if original_size > 0:
                size_ratio = estimation['size_mb'] / original_size
                compression_rate = (1 - size_ratio) * 100  # 圧縮率 = 削減された割合
                
                if compression_rate > 0:
                    text += f" 圧縮率: {compression_rate:.1f}% 削減"
                elif compression_rate < 0:
                    increase_rate = abs(compression_rate)
                    text += f" サイズ増加: {increase_rate:.1f}%"
                else:
                    text += f" サイズ変化なし"
            
            self.info_label.setText(text)
            print(f"Estimation result: {text}")  # デバッグ用
        else:
            self.info_label.setText('ファイルサイズ推定: 計算できませんでした')
            print("Estimation failed")  # デバッグ用

    def estimate_file_size(self, video_info, crf, scale_factor):
        """改良されたファイルサイズ推定アルゴリズム"""
        print(f"estimate_file_size called with CRF={crf}, scale={scale_factor}")  # デバッグ用
        
        if not video_info:
            print("No video info provided")  # デバッグ用
            return None
        
        try:
            # 基本パラメータ
            width = video_info.get('width', 0)
            height = video_info.get('height', 0)
            fps = video_info.get('fps', 0)
            duration = video_info.get('duration', 0)
            original_bitrate = video_info.get('bitrate', 0)
            original_file_size = video_info.get('file_size', 0)
            
            print(f"Video params: {width}x{height}, {fps}fps, {duration}s, {original_bitrate}kbps")  # デバッグ用
            
            if not all([width, height, fps, duration]):
                print("Missing required video parameters")  # デバッグ用
                return None
            
            # スケール後の解像度
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            # ピクセル数の比率
            pixel_ratio = (new_width * new_height) / (width * height)
            
            # === 実測データ基準の高精度推定アルゴリズム ===
            
            # 1. CRF値に基づく品質係数（実測データに基づく大幅調整）
            # 実測: CRF28で元ビットレートの約21.6%（1316/6088）になることを考慮
            if crf <= 18:
                quality_factor = 0.65 - (crf - 15) * 0.03  # CRF15-18で0.74-0.65
            elif crf <= 23:
                quality_factor = 0.65 - (crf - 18) * 0.05  # 0.65 → 0.40
            elif crf <= 28:
                quality_factor = 0.40 - (crf - 23) * 0.035  # 0.40 → 0.225
            elif crf <= 35:
                quality_factor = 0.225 - (crf - 28) * 0.02  # 0.225 → 0.085
            else:
                quality_factor = 0.085 - (crf - 35) * 0.008   # 0.085 → 0.005
            
            quality_factor = max(0.05, quality_factor)  # 最低値を保証
            
            # 2. 元動画の複雑度を考慮した基準ビットレート計算
            # 元のビットレートがある場合はそれを基準にする
            if original_bitrate and original_bitrate > 0:
                # 元ビットレートを基準にした推定（実測データ反映）
                base_bitrate = original_bitrate * quality_factor * pixel_ratio
            else:
                # 解像度とフレームレートから基準ビットレート推定
                # 実測データに基づき大幅に下方修正
                pixels_per_second = new_width * new_height * fps
                
                # 解像度別基準値（kbps per million pixels per second）- 実測基準に修正
                if new_width * new_height <= 720 * 480:    # SD
                    bitrate_per_mpps = 0.8  # 1.8 → 0.8
                elif new_width * new_height <= 1280 * 720: # HD
                    bitrate_per_mpps = 0.6  # 1.5 → 0.6
                elif new_width * new_height <= 1920 * 1080: # FHD
                    bitrate_per_mpps = 0.5  # 1.2 → 0.5
                else:  # 4K以上
                    bitrate_per_mpps = 0.4  # 1.0 → 0.4
                
                base_bitrate = (pixels_per_second / 1000000) * bitrate_per_mpps * 1000 * quality_factor
            
            # 3. フレームレート補正
            # 30fps基準で調整
            fps_factor = min(1.5, max(0.7, fps / 30.0))
            base_bitrate *= fps_factor
            
            # 4. 動画長による補正（短い動画は効率が悪い）
            if duration < 30:
                duration_factor = 1.15  # 短い動画は15%増し（30%→15%に減少）
            elif duration < 120:
                duration_factor = 1.08  # 2分未満は8%増し（15%→8%に減少）
            else:
                duration_factor = 1.0
            
            base_bitrate *= duration_factor
            
            # 5. スケールファクターによる微調整
            # スケールアップ時は効率が落ちる
            if scale_factor > 1.0:
                scale_penalty = 1.0 + (scale_factor - 1.0) * 0.1  # 0.2 → 0.1に減少
                base_bitrate *= scale_penalty
            
            # 最終ビットレート（最小値を保証）
            estimated_bitrate = max(100, base_bitrate)  # 150→100に戻す
            
            # 6. ファイルサイズ計算（オーバーヘッド考慮）
            # 音声ビットレート推定（実測に近い値）
            audio_bitrate = 128
            total_bitrate = estimated_bitrate + audio_bitrate
            
            # コンテナオーバーヘッド（実測データに基づき調整）
            container_overhead = 1.02  # 1.05 → 1.02（2%に減少）
            
            estimated_size = (total_bitrate * duration * container_overhead) / (8 * 1024)  # MB
            
            # 7. 結果の妥当性チェック
            # 元ファイルサイズと比較して極端な値を補正（範囲を緩和）
            if original_file_size > 0:
                size_ratio = estimated_size / original_file_size
                
                # 15倍以上または1/15以下の場合は補正（10倍→15倍に緩和）
                if size_ratio > 15:
                    estimated_size = original_file_size * 8  # 最大8倍に制限（5倍→8倍）
                    estimated_bitrate = (estimated_size * 8 * 1024) / duration - audio_bitrate
                elif size_ratio < 0.067:  # 1/15
                    estimated_size = original_file_size * 0.15  # 最小15%に制限（20%→15%）
                    estimated_bitrate = (estimated_size * 8 * 1024) / duration - audio_bitrate
            
            result = {
                'bitrate': round(max(150, estimated_bitrate)),  # 100→150
                'size_mb': round(max(0.1, estimated_size), 1),
                'new_resolution': f"{new_width}x{new_height}",
                'pixel_ratio': round(pixel_ratio, 2),
                'quality_factor': round(quality_factor, 2),
                'fps_factor': round(fps_factor, 2)
            }
            
            print(f"Realistic estimation result: {result}")  # デバッグ用
            return result
            
        except Exception as e:
            print(f"ファイルサイズ推定エラー: {e}")
            return None

    def update_size_estimation(self):
        """ファイルサイズ推定を更新"""
        print("update_size_estimation called")  # デバッグ用
        
        video_info = self.text_edit.video_info
        if not video_info:
            self.info_label.setText('ファイルサイズ推定: 動画ファイルを選択してください')
            print("No video info available")  # デバッグ用
            return
        
        crf = self.crf_slider.value()
        scale_factor = self.vf_slider.value() / 10.0
        
        print(f"Calculating with CRF={crf}, scale={scale_factor}")  # デバッグ用
        
        estimation = self.estimate_file_size(video_info, crf, scale_factor)
        
        if estimation:
            original_size = video_info.get('file_size', 0)
            
            text = f"ファイルサイズ推定: {estimation['size_mb']} MB "
            text += f"(元: {original_size} MB) "
            text += f"解像度: {estimation['new_resolution']} "
            text += f"推定ビットレート: {estimation['bitrate']} kbps"
            
            if original_size > 0:
                size_ratio = estimation['size_mb'] / original_size
                compression_rate = (1 - size_ratio) * 100  # 圧縮率 = 削減された割合
                
                if compression_rate > 0:
                    text += f" 圧縮率: {compression_rate:.1f}% 削減"
                elif compression_rate < 0:
                    increase_rate = abs(compression_rate)
                    text += f" サイズ増加: {increase_rate:.1f}%"
                else:
                    text += f" サイズ変化なし"
            
            self.info_label.setText(text)
            print(f"Estimation result: {text}")  # デバッグ用
        else:
            self.info_label.setText('ファイルサイズ推定: 計算できませんでした')
            print("Estimation failed")  # デバッグ用

    def show_ffmpeg_version(self):
        # 最初にウォーターマークを表示
        
        ffmpeg_path = get_ffmpeg_executable_path('ffmpeg.exe')
        ffprobe_path = get_ffmpeg_executable_path('ffprobe.exe')
        
        # FFmpegのチェック
        try:
            # Windowsでコマンドプロンプトウィンドウを表示しないための設定
            kwargs = {'capture_output': True, 'text': True, 'check': True}
            if os.name == 'nt':  # Windows環境の場合
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = startupinfo
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run([ffmpeg_path, '-version'], **kwargs)
            first_line = result.stdout.splitlines()[0] if result.stdout else ''
            self.text_edit.add_log("FFmpegが正常に検出されました")
            self.text_edit.add_log(f"FFmpeg: {first_line}")
        except Exception as e:
            self.text_edit.add_log("FFmpegのセットアップエラー")
            self.text_edit.add_log(f"FFmpegエラー: {str(e)}")
            self.text_edit.add_log("アプリケーションを使用できません。FFmpegの設定を確認してください。")
            # エラー時は赤い背景
            self.current_status = 'error'
            self.ffmpeg_available = False
            ThemeManager.apply_status_background(self.text_edit, self.current_theme, 'error')
            self.text_edit.update_display()
            # ドラッグアンドドロップを無効化
            self.disable_drag_and_drop()
            return
        
        # FFprobeのチェック
        try:
            # Windowsでコマンドプロンプトウィンドウを表示しないための設定
            kwargs = {'capture_output': True, 'text': True, 'check': True}
            if os.name == 'nt':  # Windows環境の場合
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = startupinfo
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run([ffprobe_path, '-version'], **kwargs)
            first_line = result.stdout.splitlines()[0] if result.stdout else ''
            self.text_edit.add_log("FFprobeが正常に検出されました")
            self.text_edit.add_log(f"FFprobe: {first_line}")
            
            # 両方とも正常なら緑い背景
            self.current_status = 'success'
            self.ffmpeg_available = True
            ThemeManager.apply_status_background(self.text_edit, self.current_theme, 'success')
            self.text_edit.update_display()
            
            # 初回のタイトルバーテーマ設定
            QTimer.singleShot(100, self.apply_titlebar_theme)
            
        except Exception as e:
            self.text_edit.add_log("FFprobeのセットアップエラー")
            self.text_edit.add_log(f"FFprobeエラー: {str(e)}")
            self.text_edit.add_log("動画情報取得機能が利用できません")
            # FFmpegは正常だがFFprobeに問題がある場合は黄色い背景
            self.current_status = 'warning'
            self.ffmpeg_available = True  # FFmpegは正常なので変換は可能
            ThemeManager.apply_status_background(self.text_edit, self.current_theme, 'warning')
            self.text_edit.update_display()
            
            # 初回のタイトルバーテーマ設定
            QTimer.singleShot(100, self.apply_titlebar_theme)

    def disable_drag_and_drop(self):
        """ドラッグアンドドロップ機能を無効化"""
        self.text_edit.setAcceptDrops(False)
        self.convert_button.setEnabled(False)
        self.mode_button.setEnabled(False)
        self.size_slider.setEnabled(False)
        self.crf_slider.setEnabled(False)
        self.vf_slider.setEnabled(False)
        self.text_edit.add_log("ドラッグアンドドロップ機能が無効化されました")
        self.text_edit.add_log("変換機能が無効化されました")
        self.text_edit.add_log("変換方式切替機能が無効化されました")
        self.text_edit.add_log("スライダー操作機能が無効化されました")

    def start_conversion(self):
        """動画変換を開始"""
        video_file = self.get_selected_video_file()
        if not video_file:
            self.text_edit.add_log("エラー: 動画ファイルが選択されていません")
            return
        
        # タスクバープログレスを初期化
        if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
            self.taskbar_progress.set_progress(0, 100)
            self.taskbar_progress.set_visible(True)
        
        # 出力ファイル名生成
        input_filename = os.path.basename(video_file)
        name_without_ext = os.path.splitext(input_filename)[0]
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        
        # コーデック識別子
        codec_suffix = "_H265" if self.use_h265_encoding else ""
        
        if self.encoding_mode == 'twopass':
            output_filename = f"ClipItBro_{timestamp}_2pass{codec_suffix}_{name_without_ext}.mp4"
        else:
            output_filename = f"ClipItBro_{timestamp}_CRF{codec_suffix}_{name_without_ext}.mp4"
            
        output_path = os.path.join(os.path.dirname(video_file), output_filename)
        
        # ログ出力
        codec_name = "H.265 (HEVC)" if self.use_h265_encoding else "H.264 (x264)"
        self.text_edit.add_log(f"=== {self.encoding_mode.upper()}変換開始 ===")
        self.text_edit.add_log(f"🎥 コーデック: {codec_name}")
        self.text_edit.add_log(f"入力ファイル: {input_filename}")
        self.text_edit.add_log(f"出力ファイル: {output_filename}")
        
        # エンコード方式に応じて処理分岐
        if self.encoding_mode == 'twopass':
            self.start_twopass_conversion(video_file, output_path)
        else:
            self.start_crf_conversion(video_file, output_path)

    def start_twopass_conversion(self, video_file, output_path):
        """2pass変換を開始"""
        video_info = self.text_edit.video_info
        if not video_info:
            self.text_edit.add_log("エラー: 動画情報が取得されていません")
            return
        
        # 1passデータとコーデック設定の整合性チェック
        if hasattr(self.text_edit, 'first_pass_completed') and self.text_edit.first_pass_completed:
            if hasattr(self.text_edit, 'first_pass_codec'):
                current_codec = 'H.265' if self.use_h265_encoding else 'H.264'
                if self.text_edit.first_pass_codec != current_codec:
                    self.text_edit.add_log("⚠️ 1passデータとコーデック設定が不整合です")
                    self.text_edit.add_log(f"1pass時: {self.text_edit.first_pass_codec}, 現在: {current_codec}")
                    self.text_edit.add_log("1passデータを破棄して再解析を実行します...")
                    
                    # 1passデータをリセット
                    self.text_edit.first_pass_completed = False
                    self.text_edit.first_pass_data = None
                    if hasattr(self.text_edit, '_first_pass_running'):
                        self.text_edit._first_pass_running = False
        
        # パラメータ取得
        target_size = self.size_slider.value()
        duration = video_info.get('duration', 0)
        
        if duration <= 0:
            self.text_edit.add_log("エラー: 動画の長さが不明です")
            return
        
        # ビットレート計算
        target_bitrate = self.calculate_target_bitrate(target_size, duration)
        if not target_bitrate:
            self.text_edit.add_log("エラー: ビットレート計算に失敗しました")
            return
        
        self.text_edit.add_log(f"目標サイズ: {target_size} MB")
        self.text_edit.add_log(f"推定ビットレート: {target_bitrate} kbps")
        
        # 1pass目が完了しているかチェック
        if not getattr(self.text_edit, 'first_pass_completed', False):
            self.text_edit.add_log("警告: 1pass解析が完了していません。1pass目から開始します...")
            # 1pass目を実行してから2pass目を実行
            self.execute_full_twopass(video_file, output_path, target_bitrate)
        else:
            self.text_edit.add_log("1pass解析済み。2pass目を実行します...")
            # 2pass目のみ実行
            self.execute_second_pass_only(video_file, output_path, target_bitrate)

    def execute_full_twopass(self, video_file, output_path, target_bitrate):
        """1pass目と2pass目を連続実行"""
        # 動画の総時間を取得（プログレス計算用）
        total_duration = self.text_edit.video_info.get('duration', 0) if self.text_edit.video_info else 0
        
        # ボタンを無効化と2passプログレスバー表示
        self.convert_button.setEnabled(False)
        self.convert_button.setText('変換中... (1pass)')
        self.twopass_progress_widget.setVisible(True)
        self.pass1_progress_bar.setValue(0)
        self.pass2_progress_bar.setValue(0)
        
        # 環境変数設定
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        if os.name == 'nt':
            env['LANG'] = 'ja_JP.UTF-8'
        
        try:
            # 2pass変換用のスレッドを作成
            self.conversion_thread = TwoPassConversionThread(
                video_file, output_path, target_bitrate, total_duration, use_h265=self.use_h265_encoding
            )
            self.conversion_thread.log_signal.connect(self.text_edit.add_log)
            self.conversion_thread.progress_signal.connect(self.update_twopass_progress)
            self.conversion_thread.phase_signal.connect(self.update_conversion_phase)
            self.conversion_thread.finished_signal.connect(self.conversion_finished)
            self.conversion_thread.start()
            
        except Exception as e:
            self.text_edit.add_log(f"2pass変換開始エラー: {e}")
            self.convert_button.setEnabled(True)
            self.convert_button.setText('変換実行 (2pass)')

    def execute_second_pass_only(self, video_file, output_path, target_bitrate):
        """2pass目のみ実行（1pass目は完了済み）"""
        # FFmpegコマンド構築（2pass目）
        ffmpeg_path = get_ffmpeg_executable_path('ffmpeg.exe')
        
        # コーデック選択
        video_codec = 'libx265' if self.use_h265_encoding else 'libx264'
        codec_name = 'H.265 (HEVC)' if self.use_h265_encoding else 'H.264 (x264)'
        self.text_edit.add_log(f"📹 使用コーデック: {codec_name}")
        
        cmd = [
            ffmpeg_path,
            '-y',  # ファイル上書き許可
            '-i', video_file,
            '-c:v', video_codec,
            '-b:v', f'{target_bitrate}k',
            '-pass', '2',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path
        ]
        
        # ボタンを無効化（2pass目のみ実行）
        self.convert_button.setEnabled(False)
        self.convert_button.setText('変換中... (2pass)')
        # 1pass目は100%のまま、2pass目を0%からスタート
        self.pass2_progress_bar.setValue(0)
        
        # 動画の総時間を取得（プログレス計算用）
        total_duration = self.text_edit.video_info.get('duration', 0) if self.text_edit.video_info else 0
        
        # 環境変数設定
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        if os.name == 'nt':
            env['LANG'] = 'ja_JP.UTF-8'
        
        try:
            self.text_edit.add_log("2pass目実行開始...")
            # 2pass目のプログレスバー更新のためTwoPassConversionThreadを使用
            self.twopass_thread = TwoPassConversionThread(
                video_file, output_path, target_bitrate, total_duration, 
                second_pass_only=True, use_h265=self.use_h265_encoding
            )
            self.twopass_thread.log_signal.connect(self.text_edit.add_log)
            self.twopass_thread.progress_signal.connect(self.update_twopass_progress)
            self.twopass_thread.finished_signal.connect(self.conversion_finished)
            self.twopass_thread.start()
            
        except Exception as e:
            self.text_edit.add_log(f"2pass目開始エラー: {e}")
            self.convert_button.setEnabled(True)
            self.convert_button.setText('変換実行 (2pass)')

    def start_crf_conversion(self, video_file, output_path):
        """CRF変換を開始（従来の方式）"""
        # パラメータ取得
        crf = self.crf_slider.value()
        vf = self.vf_slider.value() / 10.0
        
        self.text_edit.add_log(f"CRF: {crf}, スケール: {vf}")
        
        # FFmpegコマンド構築
        ffmpeg_path = get_ffmpeg_executable_path('ffmpeg.exe')
        cmd = [
            ffmpeg_path,
            '-i', video_file,
            '-c:v', 'libx264',
            '-crf', str(crf),
            '-vf', f'scale=trunc(iw*{vf}/2)*2:trunc(ih*{vf}/2)*2',
            '-c:a', 'copy',
            output_path
        ]
        
        # ボタンを無効化と単一プログレスバー表示
        self.convert_button.setEnabled(False)
        self.convert_button.setText('変換中... (CRF)')
        self.single_progress_bar.setVisible(True)
        self.single_progress_bar.setValue(0)
        
        # 動画の総時間を取得（プログレス計算用）
        total_duration = self.text_edit.video_info.get('duration', 0) if self.text_edit.video_info else 0
        
        # 環境変数設定
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        if os.name == 'nt':
            env['LANG'] = 'ja_JP.UTF-8'
        
        try:
            self.text_edit.add_log("CRF変換実行開始...")
            # 従来のConversionThreadを使用
            self.conversion_thread = ConversionThread(cmd, env, output_path, total_duration)
            self.conversion_thread.log_signal.connect(self.text_edit.add_log)
            self.conversion_thread.progress_signal.connect(self.update_progress)
            self.conversion_thread.finished_signal.connect(self.conversion_finished)
            self.conversion_thread.start()
            
        except Exception as e:
            self.text_edit.add_log(f"CRF変換開始エラー: {e}")
            self.convert_button.setEnabled(True)
            self.convert_button.setText('変換実行 (CRF)')

    def update_conversion_phase(self, phase):
        """変換フェーズの更新"""
        if phase == 1:
            self.convert_button.setText('変換中... (1pass)')
        elif phase == 2:
            self.convert_button.setText('変換中... (2pass)')

    def update_first_pass_progress(self, progress_percent):
        """1pass解析のプログレスバーを更新"""
        self.pass1_progress_bar.setValue(int(progress_percent))
        
        # タスクバープログレスも更新（1pass解析は全体の25%）
        if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
            taskbar_progress = progress_percent * 0.25  # 1pass解析は全体の25%
            self.taskbar_progress.set_progress(int(taskbar_progress), 100)
        
        # 1pass解析中であることを明示
        if progress_percent < 100:
            self.convert_button.setText(f'1pass解析中... ({int(progress_percent)}%)')
        else:
            self.convert_button.setText('1pass解析完了')

    def update_twopass_progress(self, progress_percent):
        """2pass変換の全体プログレスを更新（0-100%を1pass/2passに分割）"""
        if progress_percent <= 50:
            # 0-50% : 1pass目（25-62.5%のタスクバープログレス）
            pass1_percent = int(progress_percent * 2)
            self.pass1_progress_bar.setValue(pass1_percent)
            self.pass2_progress_bar.setValue(0)
            
            # タスクバープログレス更新（25%から62.5%まで）
            if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
                taskbar_progress = 25 + (progress_percent * 0.75)  # 25% + (0-50% * 0.75)
                self.taskbar_progress.set_progress(int(taskbar_progress), 100)
        else:
            # 50-100% : 2pass目（62.5-100%のタスクバープログレス）
            self.pass1_progress_bar.setValue(100)
            pass2_percent = int((progress_percent - 50) * 2)
            self.pass2_progress_bar.setValue(pass2_percent)
            
            # タスクバープログレス更新（62.5%から100%まで）
            if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
                taskbar_progress = 62.5 + ((progress_percent - 50) * 0.75)  # 62.5% + (0-50% * 0.75)
                self.taskbar_progress.set_progress(int(taskbar_progress), 100)

    def update_progress(self, progress_percent):
        """CRF変換のプログレスバーを更新"""
        self.single_progress_bar.setValue(int(progress_percent))
        
        # タスクバープログレスも更新（CRF方式は直接的）
        if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
            self.taskbar_progress.set_progress(int(progress_percent), 100)

    def conversion_finished(self, success, output_path, error_message):
        """変換完了時の処理"""
        self.convert_button.setEnabled(True)
        if self.encoding_mode == 'twopass':
            self.convert_button.setText('変換実行 (2pass)')
            # 2passプログレスバーを非表示
            self.twopass_progress_widget.setVisible(False)
        else:
            self.convert_button.setText('変換実行 (CRF)')
            # 単一プログレスバーを非表示
            self.single_progress_bar.setVisible(False)
        
        # タスクバープログレスをクリア
        if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
            if success:
                # 成功時は100%を表示してからクリア
                self.taskbar_progress.set_progress(100, 100)
                QTimer.singleShot(1000, self.taskbar_progress.clear_progress)  # 1秒後にクリア
            else:
                # エラー時は即座にクリア
                self.taskbar_progress.clear_progress()
        
        if success:
            self.text_edit.add_log("=== 変換完了 ===")
            self.text_edit.add_log(f"出力ファイル: {os.path.basename(output_path)}")
            # 出力ファイルのサイズを取得
            try:
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                self.text_edit.add_log(f"出力ファイルサイズ: {file_size:.2f} MB")
                
                # 2pass方式の場合、目標サイズとの比較を表示
                if self.encoding_mode == 'twopass':
                    target_size = self.size_slider.value()
                    size_diff = abs(file_size - target_size)
                    accuracy = ((target_size - size_diff) / target_size) * 100
                    self.text_edit.add_log(f"目標サイズ: {target_size} MB | 誤差: {size_diff:.2f} MB | 精度: {accuracy:.1f}%")
            except:
                pass
            
            # 変換完了時にアプリをアクティブにしてタスクバーを点滅
            self.activate_window_on_completion()
                
            # 変換完了ポップアップを表示
            self.show_completion_dialog(output_path)
        else:
            self.text_edit.add_log("=== 変換失敗 ===")
            if error_message:
                self.text_edit.add_log(f"エラー: {error_message}")
            
            # エラー時もアプリをアクティブに
            self.activate_window_on_completion()
                
            # エラーポップアップを表示
            self.show_error_dialog(error_message)

    def show_completion_dialog(self, output_path):
        """変換完了ダイアログを表示"""
        
        # ファイル情報を取得
        file_name = os.path.basename(output_path)
        clipboard_copied = False
        
        # 自動クリップボードコピー設定が有効な場合、先にコピーを実行
        if self.auto_clipboard_copy:
            self.text_edit.add_log("📋 自動クリップボードコピーが有効です")
            if self.copy_file_to_clipboard(output_path, show_notification=False):
                self.text_edit.add_log("✓ 変換完了時に自動でクリップボードにコピーしました")
                clipboard_copied = True
            else:
                self.text_edit.add_log("⚠ 自動クリップボードコピーに失敗しました")
        
        # ランダム画像選択機能（ダイアログと通知で共有）
        custom_icon_path = self.get_random_completion_icon()
        
        # システム通知を表示（ランダム画像を渡す）
        self.show_conversion_completion_notification(output_path, clipboard_copied, custom_icon_path)
        
        # 親なしでQMessageBoxを作成（タイトルに自動でアプリ名が追加されるのを防ぐ）
        msg_box = QMessageBox()
        
        # ウィンドウの閉じるボタンを確実に有効にする
        msg_box.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)
        
        if custom_icon_path:
            try:
                pixmap = QPixmap(custom_icon_path)
                # アイコンサイズを調整（64x64ピクセル）
                scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                msg_box.setIconPixmap(scaled_pixmap)
                self.text_edit.add_log(f"ランダムアイコンを表示: {os.path.basename(custom_icon_path)}")
            except Exception as e:
                msg_box.setIcon(QMessageBox.Information)
                self.text_edit.add_log(f"ランダムアイコン読み込みエラー: {e}")
        else:
            # カスタムアイコンが見つからない場合はデフォルトアイコン
            msg_box.setIcon(QMessageBox.Information)
            self.text_edit.add_log("ランダム表示用の画像が見つかりません。デフォルトアイコンを使用します")
        
        msg_box.setWindowTitle("変換完了")
        msg_box.setText("動画変換が完了しました！")
        
        # ファイル情報を表示
        file_name = os.path.basename(output_path)
        try:
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            info_text = f"ファイル名: {file_name}\nファイルサイズ: {file_size:.2f} MB"
        except:
            info_text = f"ファイル名: {file_name}"
        
        msg_box.setInformativeText(info_text)
        
        # カスタムボタンを追加
        ok_button = msg_box.addButton("OK", QMessageBox.AcceptRole)
        folder_button = msg_box.addButton("フォルダを開く", QMessageBox.ActionRole)
        clipboard_button = msg_box.addButton("クリップボードにコピー", QMessageBox.ActionRole)
        
        # デフォルトボタンとエスケープボタンを設定（バツボタン対応）
        msg_box.setDefaultButton(ok_button)
        msg_box.setEscapeButton(ok_button)
        
        # ボタンにテーマスタイルを適用
        ThemeManager.apply_theme_to_widget(ok_button, self.current_theme)
        ThemeManager.apply_theme_to_widget(folder_button, self.current_theme)
        ThemeManager.apply_theme_to_widget(clipboard_button, self.current_theme)
        
        # QMessageBox全体にもテーマを適用
        msg_box_style = f"""
        QMessageBox {{
            background-color: {self.current_theme['main_bg']};
            color: {self.current_theme['text_color']};
        }}
        QMessageBox QLabel {{
            color: {self.current_theme['text_color']};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {self.current_theme['button_bg']} !important;
            color: {self.current_theme['button_text']} !important;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
            min-width: auto;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        """
        msg_box.setStyleSheet(msg_box_style)
        
        # ダイアログを表示
        result = msg_box.exec_()
        
        # クリックされたボタンを確認
        clicked_button = msg_box.clickedButton()
        
        # バツボタンまたはESCキーで閉じられた場合の判定
        if clicked_button is None or result == QMessageBox.Close:
            self.text_edit.add_log("ダイアログのバツボタン（閉じる）またはESCキーが押されました")
        elif clicked_button == folder_button:
            self.text_edit.add_log("フォルダを開くボタンがクリックされました")
            self.text_edit.add_log(f"対象ファイル: {output_path}")
            
            # ファイルの存在確認
            if os.path.exists(output_path):
                self.text_edit.add_log("出力ファイルの存在を確認しました")
                self.open_output_folder(output_path)
            else:
                self.text_edit.add_log(f"⚠ 出力ファイルが見つかりません: {output_path}")
                # フォルダのみ開く試行
                folder_path = os.path.dirname(output_path)
                if os.path.exists(folder_path):
                    self.text_edit.add_log(f"フォルダのみ開きます: {folder_path}")
                    self.open_output_folder(folder_path)
                else:
                    self.text_edit.add_log(f"⚠ フォルダも見つかりません: {folder_path}")
        
        elif clicked_button == clipboard_button:
            self.text_edit.add_log("クリップボードにコピーボタンがクリックされました")
            self.copy_file_to_clipboard(output_path, show_notification=True)
        else:
            self.text_edit.add_log("OKボタンがクリックされました")

    def copy_file_to_clipboard(self, file_path, show_notification=True):
        """変換完了したファイルをエクスプローラーと同じ形式でクリップボードにコピー"""
        try:
            from PyQt5.QtCore import QMimeData, QUrl
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                self.text_edit.add_log(f"⚠ ファイルが見つかりません: {file_path}")
                if show_notification:
                    QMessageBox.warning(self, "エラー", "ファイルが見つかりません。")
                return False
            
            # PyQt5でエクスプローラーと同じ形式でコピー
            clipboard = QApplication.clipboard()
            mime_data = QMimeData()
            
            # ファイルパスを正規化
            normalized_path = os.path.abspath(file_path)
            file_url = QUrl.fromLocalFile(normalized_path)
            mime_data.setUrls([file_url])
            
            # クリップボードにセット
            clipboard.setMimeData(mime_data)
            
            # 成功ログと通知
            filename = os.path.basename(file_path)
            self.text_edit.add_log(f"✓ ファイルをクリップボードにコピーしました: {filename}")
            
            # 成功通知ダイアログ（手動実行時のみ）
            if show_notification:
                QMessageBox.information(self, "クリップボードにコピー", 
                    f"ファイルをクリップボードにコピーしました。\n\n"
                    f"ファイル名: {filename}\n\n"
                    f"他のアプリケーションで Ctrl+V で貼り付けできます。")
            
            return True
            
        except ImportError:
            # PyQt5のQMimeDataが利用できない場合のフォールバック
            self.text_edit.add_log("⚠ PyQt5のクリップボード機能が利用できません")
            if show_notification:
                QMessageBox.warning(self, "エラー", "クリップボード機能が利用できません。")
            return False
            
        except Exception as e:
            self.text_edit.add_log(f"⚠ クリップボードコピーに失敗: {e}")
            if show_notification:
                QMessageBox.warning(self, "エラー", f"クリップボードへのコピーに失敗しました。\n\nエラー: {e}")
            return False

    def show_error_dialog(self, error_message):
        """変換エラーダイアログを表示"""
        # 親なしでQMessageBoxを作成（タイトルに自動でアプリ名が追加されるのを防ぐ）
        msg_box = QMessageBox()
        
        # ウィンドウの閉じるボタンを確実に有効にする
        msg_box.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)
        
        # ランダムエラー画像選択機能
        custom_icon_path = self.get_random_error_icon()
        
        if custom_icon_path:
            try:
                pixmap = QPixmap(custom_icon_path)
                # アイコンサイズを調整（64x64ピクセル）
                scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                msg_box.setIconPixmap(scaled_pixmap)
                self.text_edit.add_log(f"ランダムエラーアイコンを表示: {os.path.basename(custom_icon_path)}")
            except Exception as e:
                msg_box.setIcon(QMessageBox.Critical)
                self.text_edit.add_log(f"ランダムエラーアイコン読み込みエラー: {e}")
        else:
            # カスタムアイコンが見つからない場合はデフォルトアイコン
            msg_box.setIcon(QMessageBox.Critical)
            self.text_edit.add_log("ランダムエラー表示用の画像が見つかりません。デフォルトアイコンを使用します")
        
        msg_box.setWindowTitle("変換エラー")
        msg_box.setText("動画変換に失敗しました")
        msg_box.setDetailedText(error_message if error_message else "不明なエラーが発生しました")
        
        # OKボタンを追加
        ok_button = msg_box.addButton("OK", QMessageBox.AcceptRole)
        
        # ボタンにテーマスタイルを適用
        ThemeManager.apply_theme_to_widget(ok_button, self.current_theme)
        
        # QMessageBox全体にもテーマを適用
        msg_box_style = f"""
        QMessageBox {{
            background-color: {self.current_theme['main_bg']};
            color: {self.current_theme['text_color']};
        }}
        QMessageBox QLabel {{
            color: {self.current_theme['text_color']};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {self.current_theme['button_bg']} !important;
            color: {self.current_theme['button_text']} !important;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
            min-width: auto;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        """
        msg_box.setStyleSheet(msg_box_style)
        
        # ダイアログを表示
        result = msg_box.exec_()
        self.text_edit.add_log("エラーダイアログを閉じました")

    def get_random_completion_icon(self):
        """ランダムな変換完了アイコンを取得（EXE対応）"""
        def get_resource_path(relative_path):
            """EXE環境とスクリプト環境の両方でリソースパスを取得"""
            if hasattr(sys, '_MEIPASS'):
                # PyInstallerでパッケージ化された環境
                return os.path.join(sys._MEIPASS, relative_path)
            else:
                # 通常のPythonスクリプト環境
                return relative_path
        
        # サポートされる画像形式
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif', '*.svg']
        
        # 検索するフォルダパス
        search_folders = [
            'icon/completion/',  # 専用フォルダ（優先）
            'icon/random/',      # 別名フォルダ
            'icon/'              # メインフォルダ
        ]
        
        all_images = []
        
        # 各フォルダから画像ファイルを収集
        for folder in search_folders:
            resource_folder = get_resource_path(folder)
            if os.path.exists(resource_folder):
                for extension in image_extensions:
                    pattern = os.path.join(resource_folder, extension)
                    images = glob.glob(pattern)
                    all_images.extend(images)
        
        # 特定のファイル名を除外（アプリアイコンなど）
        excluded_names = ['app.ico', 'app.png', 'app.jpg', 'app.jpeg']
        filtered_images = []
        
        for image_path in all_images:
            filename = os.path.basename(image_path).lower()
            if filename not in excluded_names:
                filtered_images.append(image_path)
        
        # ランダムに選択
        if filtered_images:
            selected_image = random.choice(filtered_images)
            return selected_image
        
        # フォールバック：元の方法で単一ファイルを検索
        for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg']:
            potential_path = f"icon/success{ext}"
            resource_path = get_resource_path(potential_path)
            if os.path.exists(resource_path):
                return resource_path
        
        return None

    def get_random_error_icon(self):
        """ランダムなエラーアイコンを取得（EXE対応）"""
        def get_resource_path(relative_path):
            """EXE環境とスクリプト環境の両方でリソースパスを取得"""
            if hasattr(sys, '_MEIPASS'):
                # PyInstallerでパッケージ化された環境
                return os.path.join(sys._MEIPASS, relative_path)
            else:
                # 通常のPythonスクリプト環境
                return relative_path
        
        # サポートされる画像形式
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif', '*.svg']
        
        # 検索するフォルダパス（エラー用）
        search_folders = [
            'icon/error/',       # エラー専用フォルダ（優先）
            'icon/fail/',        # 失敗フォルダ
            'icon/warning/',     # 警告フォルダ
            'icon/'              # メインフォルダ
        ]
        
        all_images = []
        
        # 各フォルダから画像ファイルを収集
        for folder in search_folders:
            resource_folder = get_resource_path(folder)
            if os.path.exists(resource_folder):
                for extension in image_extensions:
                    pattern = os.path.join(resource_folder, extension)
                    images = glob.glob(pattern)
                    all_images.extend(images)
        
        # 特定のファイル名を除外（アプリアイコンや成功アイコンなど）
        excluded_names = [
            'app.ico', 'app.png', 'app.jpg', 'app.jpeg',  # アプリアイコン
            'success.png', 'success.jpg', 'success.jpeg', 'success.gif',  # 成功アイコン
            'logo.png', 'logo.jpg', 'logo.gif'  # ロゴ
        ]
        
        # エラー関連のキーワードでフィルタリング（優先選択）
        error_keywords = ['error', 'fail', 'warning', 'alert', 'bug', 'crash', 'sad', 'no', 'x']
        priority_images = []
        other_images = []
        
        for image_path in all_images:
            filename = os.path.basename(image_path).lower()
            # 除外リストにあるファイルはスキップ
            if filename in excluded_names:
                continue
                
            # エラー関連キーワードを含むファイルを優先
            if any(keyword in filename for keyword in error_keywords):
                priority_images.append(image_path)
            else:
                other_images.append(image_path)
        
        # 優先画像がある場合はそこからランダム選択
        if priority_images:
            selected_image = random.choice(priority_images)
            return selected_image
        
        # 優先画像がない場合は他の画像からランダム選択
        if other_images:
            selected_image = random.choice(other_images)
            return selected_image
        
        # フォールバック：特定のエラーアイコンを検索
        for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.svg']:
            for error_name in ['error', 'fail', 'warning', 'alert']:
                potential_path = f"icon/{error_name}{ext}"
                resource_path = get_resource_path(potential_path)
                if os.path.exists(resource_path):
                    return resource_path
        
        return None

    def open_output_folder(self, file_path):
        """出力ファイルのフォルダを開く（EXE対応完全版）"""
        try:
            import subprocess
            import platform
            
            # ファイルパスの存在確認
            if not file_path or not os.path.exists(file_path):
                self.text_edit.add_log(f"エラー: ファイルが存在しません: {file_path}")
                return
            
            folder_path = os.path.dirname(file_path)
            abs_file_path = os.path.abspath(file_path)
            abs_folder_path = os.path.abspath(folder_path)
            
            self.text_edit.add_log(f"フォルダオープン試行: {abs_folder_path}")
            self.text_edit.add_log(f"ターゲットファイル: {abs_file_path}")
            
            if platform.system() == "Windows":
                # 方法1: Windows API (ShellExecute) を使用
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # ShellExecuteWの定義
                    shell32 = ctypes.windll.shell32
                    
                    # ファイルを選択してエクスプローラーを開く
                    self.text_edit.add_log("Windows API (ShellExecute)でファイル選択を試行")
                    result = shell32.ShellExecuteW(
                        None,                    # hwnd
                        "open",                  # verb
                        "explorer.exe",          # file
                        f'/select,"{abs_file_path}"',  # parameters
                        None,                    # directory
                        1                        # SW_SHOWNORMAL
                    )
                    
                    if result > 32:  # 成功
                        self.text_edit.add_log(f"✓ Windows API でファイル選択成功: {abs_file_path}")
                        return
                    else:
                        self.text_edit.add_log(f"Windows API実行失敗 (code: {result})")
                        
                except Exception as e:
                    self.text_edit.add_log(f"Windows API実行エラー: {e}")
                
                # 方法2: subprocess.Popen（非同期実行）
                try:
                    self.text_edit.add_log("フォールバック1: subprocess.Popenでファイル選択を試行")
                    
                    # 正規化されたパスを使用
                    normalized_path = os.path.normpath(abs_file_path)
                    cmd = ['explorer', '/select,', f'"{normalized_path}"']
                    
                    self.text_edit.add_log(f"実行コマンド: {' '.join(cmd)}")
                    
                    # Popenで非同期実行
                    process = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    # プロセスが正常に開始されたかチェック
                    import time
                    time.sleep(0.5)  # 少し待機
                    
                    if process.poll() is None or process.returncode == 0:
                        self.text_edit.add_log(f"✓ subprocess.Popenでファイル選択成功: {abs_file_path}")
                        return
                    else:
                        self.text_edit.add_log(f"subprocess.Popen実行失敗 (code: {process.returncode})")
                        
                except Exception as e:
                    self.text_edit.add_log(f"subprocess.Popen実行エラー: {e}")
                
                # 方法3: Windows API でフォルダのみ開く
                try:
                    import ctypes
                    
                    self.text_edit.add_log("フォールバック2: Windows APIでフォルダオープンを試行")
                    shell32 = ctypes.windll.shell32
                    
                    result = shell32.ShellExecuteW(
                        None,                    # hwnd
                        "open",                  # verb
                        abs_folder_path,         # file (フォルダパス)
                        None,                    # parameters
                        None,                    # directory
                        1                        # SW_SHOWNORMAL
                    )
                    
                    if result > 32:  # 成功
                        self.text_edit.add_log(f"✓ Windows API でフォルダオープン成功: {abs_folder_path}")
                        return
                    else:
                        self.text_edit.add_log(f"Windows API フォルダオープン失敗 (code: {result})")
                        
                except Exception as e:
                    self.text_edit.add_log(f"Windows API フォルダオープンエラー: {e}")
                
                # 方法4: subprocess.Popenでフォルダのみ開く
                try:
                    self.text_edit.add_log("フォールバック3: subprocess.Popenでフォルダオープンを試行")
                    
                    cmd = ['explorer', abs_folder_path]
                    process = subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    import time
                    time.sleep(0.5)
                    
                    if process.poll() is None or process.returncode == 0:
                        self.text_edit.add_log(f"✓ subprocess.Popenでフォルダオープン成功: {abs_folder_path}")
                        return
                    else:
                        self.text_edit.add_log(f"subprocess.Popen フォルダオープン失敗 (code: {process.returncode})")
                        
                except Exception as e:
                    self.text_edit.add_log(f"subprocess.Popen フォルダオープンエラー: {e}")
                    
            elif platform.system() == "Darwin":  # macOS
                try:
                    subprocess.run(['open', '-R', abs_file_path], check=True)
                    self.text_edit.add_log(f"✓ Finderでフォルダを開きました: {abs_folder_path}")
                    return
                except Exception as e:
                    self.text_edit.add_log(f"macOS open実行エラー: {e}")
                    
            else:  # Linux
                try:
                    subprocess.run(['xdg-open', abs_folder_path], check=True)
                    self.text_edit.add_log(f"✓ フォルダを開きました: {abs_folder_path}")
                    return
                except Exception as e:
                    self.text_edit.add_log(f"Linux xdg-open実行エラー: {e}")
            
            # 全ての方法が失敗した場合
            self.text_edit.add_log("⚠ 全ての方法でフォルダオープンに失敗しました")
            
        except Exception as e:
            self.text_edit.add_log(f"フォルダオープン処理で予期しないエラー: {e}")
            import traceback
            self.text_edit.add_log(f"詳細エラー: {traceback.format_exc()}")

    def get_selected_video_file(self):
        """現在選択されている動画ファイルのパスを取得"""
        return self.text_edit.video_file_path

    def activate_window_on_completion(self):
        """変換完了時にアプリをアクティブにしてタスクバーを点滅"""
        try:
            import platform
            
            if platform.system() == "Windows":
                # Windows APIを使用してタスクバー点滅とウィンドウアクティブ化
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # ウィンドウハンドルを取得
                    hwnd = int(self.winId())
                    self.text_edit.add_log(f"ウィンドウハンドル: {hwnd}")
                    
                    # Windows API定義
                    user32 = ctypes.windll.user32
                    
                    # FLASHWINFO構造体定義
                    class FLASHWINFO(ctypes.Structure):
                        _fields_ = [
                            ("cbSize", wintypes.UINT),
                            ("hwnd", wintypes.HWND),
                            ("dwFlags", wintypes.DWORD),
                            ("uCount", wintypes.UINT),
                            ("dwTimeout", wintypes.DWORD)
                        ]
                    
                    # フラッシュ設定定数
                    FLASHW_STOP = 0x0
                    FLASHW_CAPTION = 0x1    # タイトルバーを点滅
                    FLASHW_TRAY = 0x2       # タスクバーを点滅
                    FLASHW_ALL = FLASHW_CAPTION | FLASHW_TRAY  # 両方点滅
                    FLASHW_TIMER = 0x4      # 継続的に点滅
                    FLASHW_TIMERNOFG = 0x12 # フォアグラウンドになるまで点滅
                    
                    # FLASHWINFO設定
                    flash_info = FLASHWINFO()
                    flash_info.cbSize = ctypes.sizeof(FLASHWINFO)
                    flash_info.hwnd = hwnd
                    flash_info.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
                    flash_info.uCount = 3  # 3回点滅
                    flash_info.dwTimeout = 0  # デフォルトタイミング
                    
                    # タスクバー点滅実行
                    result = user32.FlashWindowEx(ctypes.byref(flash_info))
                    self.text_edit.add_log(f"タスクバー点滅実行: {result}")
                    
                    # ウィンドウを前面に持ってくる
                    user32.SetForegroundWindow(hwnd)
                    self.text_edit.add_log("ウィンドウを前面に移動")
                    
                    # アクティブ化
                    user32.SetActiveWindow(hwnd)
                    self.text_edit.add_log("ウィンドウをアクティブ化")
                    
                    # Qtのウィンドウアクティブ化も実行
                    self.raise_()
                    self.activateWindow()
                    self.text_edit.add_log("Qt ウィンドウアクティブ化完了")
                    
                except Exception as e:
                    self.text_edit.add_log(f"Windows API実行エラー: {e}")
                    # フォールバック: Qtの標準機能のみ使用
                    self.raise_()
                    self.activateWindow()
                    self.text_edit.add_log("フォールバック: Qt標準アクティブ化")
                    
            else:
                # Windows以外のプラットフォーム
                self.raise_()
                self.activateWindow()
                self.text_edit.add_log("非Windows環境: Qt標準アクティブ化")
                
        except Exception as e:
            self.text_edit.add_log(f"ウィンドウアクティブ化エラー: {e}")
            # 最終フォールバック
            try:
                self.raise_()
                self.activateWindow()
                self.text_edit.add_log("最終フォールバック: 基本アクティブ化")
            except Exception as e2:
                self.text_edit.add_log(f"最終フォールバックもエラー: {e2}")

    def create_checkmark_icon(self, checked=True, theme=None):
        """チェックマークアイコンを作成"""
        if theme is None:
            theme = self.current_theme
        
        from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
        from PyQt5.QtCore import Qt
        
        # 12x12のピクセルマップを作成
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if checked:
            # チェックマークを描画
            pen = QPen()
            # 背景色との強いコントラストを確保
            if theme['name'] == 'Dark':
                pen.setColor(QColor('#ffffff'))  # ダークテーマでは白
            else:
                pen.setColor(QColor('#000000'))  # ライトテーマでは黒
            pen.setWidth(2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            
            # チェックマークのパスを描画（少し中央寄りに）
            painter.drawLine(3, 6, 5, 8)
            painter.drawLine(5, 8, 9, 4)
        
        painter.end()
        return QIcon(pixmap)

    def update_menu_checkmarks(self):
        """メニューのチェックマーク表示を更新"""
        # テーマメニューの更新
        for action in self.theme_group.actions():
            if action.isChecked():
                action.setIcon(self.create_checkmark_icon(True))
            else:
                action.setIcon(QIcon())  # アイコンをクリア
        
        # クリップボードアクションの更新
        if hasattr(self, 'auto_clipboard_action'):
            if self.auto_clipboard_action.isChecked():
                self.auto_clipboard_action.setIcon(self.create_checkmark_icon(True))
            else:
                self.auto_clipboard_action.setIcon(QIcon())
        
        # H.265エンコードアクションの更新
        if hasattr(self, 'h265_action'):
            if self.h265_action.isChecked():
                self.h265_action.setIcon(self.create_checkmark_icon(True))
            else:
                self.h265_action.setIcon(QIcon())

    def create_menu_bar(self):
        """メニューバーを作成"""
        menubar = self.menuBar()
        
        # 設定メニュー
        settings_menu = menubar.addMenu('設定')
        
        # テーマサブメニュー
        theme_menu = settings_menu.addMenu('テーマ')
        
        # テーマアクショングループ（排他選択）
        self.theme_group = QActionGroup(self)
        
        # ライトテーマアクション
        light_action = QAction('ライト', self)
        light_action.setCheckable(True)
        light_action.setChecked(self.current_theme['name'] == 'Light')
        light_action.triggered.connect(lambda: self.change_theme('light'))
        self.theme_group.addAction(light_action)
        theme_menu.addAction(light_action)
        
        # ダークテーマアクション
        dark_action = QAction('ダーク', self)
        dark_action.setCheckable(True)
        dark_action.setChecked(self.current_theme['name'] == 'Dark')
        dark_action.triggered.connect(lambda: self.change_theme('dark'))
        self.theme_group.addAction(dark_action)
        theme_menu.addAction(dark_action)
        
        # セパレーター追加
        settings_menu.addSeparator()
        
        # クリップボード自動コピー設定
        self.auto_clipboard_action = QAction('変換完了時にクリップボードへコピー', self)
        self.auto_clipboard_action.setCheckable(True)
        self.auto_clipboard_action.setChecked(self.auto_clipboard_copy)
        self.auto_clipboard_action.triggered.connect(self.toggle_auto_clipboard_copy)
        settings_menu.addAction(self.auto_clipboard_action)
        
        # H.265エンコード設定（試験的機能）
        self.h265_action = QAction('(試験的) H.265エンコードを使用', self)
        self.h265_action.setCheckable(True)
        self.h265_action.setChecked(self.use_h265_encoding)
        self.h265_action.triggered.connect(self.toggle_h265_encoding)
        settings_menu.addAction(self.h265_action)
        
        # セパレーター追加
        settings_menu.addSeparator()
        
        # おみくじ（デバッグ用）
        test_notification_action = QAction('おみくじ', self)
        test_notification_action.triggered.connect(self.test_notification)
        settings_menu.addAction(test_notification_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu('ヘルプ')
        
        # Aboutアクション
        about_action = QAction('ClipItBro について', self)
        about_action.setShortcut('F1')
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        # アップデートメニュー（最初は非表示）
        self.update_menu_action = QAction('🔔 アップデートがあります！', self)
        self.update_menu_action.triggered.connect(self.show_update_dialog)
        self.update_menu_action.setVisible(False)  # 最初は非表示
        menubar.addAction(self.update_menu_action)
        
        # チェックマーク表示を更新
        self.update_menu_checkmarks()
    
    def show_about_dialog(self):
        """Aboutダイアログを表示"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()
    
    def showEvent(self, event):
        """ウィンドウが表示された時の処理"""
        super().showEvent(event)
        # タスクバープログレスボタンを初期化
        if hasattr(self, 'taskbar_progress') and self.taskbar_progress:
            self.taskbar_progress.set_window(self)
        
        # タスクバー統合の最終確認（ウィンドウ表示後）- テスト用に無効化
        # if hasattr(self, 'ensure_taskbar_integration'):
        #     QTimer.singleShot(200, self.ensure_taskbar_integration)
        print("showEvent: タスクバー統合の最終確認を無効化中（テスト）")
    
    def load_theme_setting(self):
        """設定からテーマを読み込み"""
        theme_name = self.settings.value('theme', 'Light')
        if theme_name == 'Dark':
            self.current_theme = ThemeManager.DARK_THEME
        else:
            self.current_theme = ThemeManager.LIGHT_THEME
    
    def save_theme_setting(self):
        """テーマ設定を保存"""
        self.settings.setValue('theme', self.current_theme['name'])
    
    def toggle_auto_clipboard_copy(self):
        """自動クリップボードコピー設定を切り替え"""
        self.auto_clipboard_copy = self.auto_clipboard_action.isChecked()
        self.settings.setValue('auto_clipboard_copy', self.auto_clipboard_copy)
        
        # チェックマーク表示を更新
        self.update_menu_checkmarks()
        
        # ログに設定変更を記録
        status = "有効" if self.auto_clipboard_copy else "無効"
        self.text_edit.add_log(f"📋 変換完了時の自動クリップボードコピー: {status}")
    
    def toggle_h265_encoding(self):
        """H.265エンコード設定を切り替え（試験的機能）"""
        self.use_h265_encoding = self.h265_action.isChecked()
        self.settings.setValue('use_h265_encoding', self.use_h265_encoding)
        
        # 1pass実行中の場合は強制停止
        if hasattr(self.text_edit, '_first_pass_running') and self.text_edit._first_pass_running:
            self.text_edit.add_log("⚠️ 1pass実行中にコーデック変更が検出されました")
            self.text_edit.add_log("🛑 安全のため1pass処理を停止します...")
            
            # 実行中のfirst_pass_threadを停止
            if hasattr(self, 'first_pass_thread') and self.first_pass_thread and self.first_pass_thread.isRunning():
                self.first_pass_thread.stop()
                self.first_pass_thread.wait(3000)  # 最大3秒待機
                if self.first_pass_thread.isRunning():
                    self.first_pass_thread.terminate()  # 強制終了
                    self.first_pass_thread.wait(1000)
                self.text_edit.add_log("✓ 1pass処理を停止しました")
            
            # text_edit内のfirst_pass_threadも停止
            if hasattr(self.text_edit, 'first_pass_thread') and self.text_edit.first_pass_thread and self.text_edit.first_pass_thread.isRunning():
                self.text_edit.first_pass_thread.stop()
                self.text_edit.first_pass_thread.wait(3000)
                if self.text_edit.first_pass_thread.isRunning():
                    self.text_edit.first_pass_thread.terminate()
                    self.text_edit.first_pass_thread.wait(1000)
            
            # 1passの一時ファイルをクリーンアップ
            try:
                temp_files = ['ffmpeg2pass-0.log', 'ffmpeg2pass-0.log.mbtree']
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        self.text_edit.add_log(f"🗑️ 一時ファイルを削除: {temp_file}")
            except Exception as e:
                self.text_edit.add_log(f"⚠️ 一時ファイル削除エラー: {e}")
        
        # コーデック変更時は1passデータを破棄（H.264とH.265で互換性がないため）
        if hasattr(self.text_edit, 'first_pass_completed') and self.text_edit.first_pass_completed:
            self.text_edit.first_pass_completed = False
            self.text_edit.first_pass_data = None
            if hasattr(self.text_edit, 'first_pass_codec'):
                self.text_edit.first_pass_codec = None
            if hasattr(self.text_edit, '_first_pass_running'):
                self.text_edit._first_pass_running = False
            
            # プログレスバーを0%にリセット
            self.pass1_progress_bar.setValue(0)
            self.pass2_progress_bar.setValue(0)
            
            # 変換ボタンを無効化（1pass再実行が必要）
            self.convert_button.setEnabled(False)
            self.convert_button.setText('1pass解析開始')
            
            self.text_edit.add_log("⚠️ コーデック変更により1pass解析データを破棄しました")
        
        # 実行中フラグのリセット（停止処理後に確実にクリア）
        if hasattr(self.text_edit, '_first_pass_running'):
            self.text_edit._first_pass_running = False
        
        # プログレスバーを0%にリセット（実行中停止の場合も対応）
        self.pass1_progress_bar.setValue(0)
        self.pass2_progress_bar.setValue(0)
        
        # 変換ボタンの状態を適切に設定
        if self.text_edit.video_file_path and self.encoding_mode == 'twopass':
            self.convert_button.setEnabled(True)
            self.convert_button.setText('1pass解析開始')
        elif self.text_edit.video_file_path and self.encoding_mode == 'crf':
            self.convert_button.setEnabled(True)
            self.convert_button.setText('変換実行 (CRF)')
        else:
            self.convert_button.setEnabled(False)
        
        # チェックマーク表示を更新
        self.update_menu_checkmarks()
        
        # ログに設定変更を記録
        codec_name = "H.265 (HEVC)" if self.use_h265_encoding else "H.264 (x264)"
        status = "有効" if self.use_h265_encoding else "無効"
        self.text_edit.add_log(f"🎬 H.265エンコード（試験的機能）: {status}")
        self.text_edit.add_log(f"📹 使用コーデック: {codec_name}")
        
        if self.use_h265_encoding:
            self.text_edit.add_log("⚠️ H.265は高効率ですが、一部デバイスで再生できない場合があります")
        
        # H.265警告バーの表示切り替え
        self.update_h265_warning_bar()
    
    def update_h265_warning_bar(self):
        """H.265警告バーの表示状態を更新"""
        if hasattr(self, 'h265_warning_bar'):
            if self.use_h265_encoding:
                # テーマに応じて警告バーの色を調整
                if hasattr(self, 'current_theme') and self.current_theme['name'] == 'Dark':
                    # ダークテーマ用の色
                    self.h265_warning_bar.setStyleSheet("""
                        QLabel {
                            background-color: #4a1a1a;
                            color: #ff8a80;
                            border: 1px solid #d32f2f;
                            padding: 4px;
                            font-weight: bold;
                            font-size: 11px;
                        }
                    """)
                else:
                    # ライトテーマ用の色
                    self.h265_warning_bar.setStyleSheet("""
                        QLabel {
                            background-color: #ffebee;
                            color: #c62828;
                            border: 1px solid #ef5350;
                            padding: 4px;
                            font-weight: bold;
                            font-size: 11px;
                        }
                    """)
                self.h265_warning_bar.setVisible(True)
            else:
                self.h265_warning_bar.setVisible(False)
    
    def test_notification(self):
        """通知機能をテスト"""
        self.text_edit.add_log("🧪 通知テストを実行します...")
        
        # テスト通知を表示（複数通知システムを試行）
        title = f"⛩️ おみくじ（通知テスト）"
        message = "通知のテストだよ～"
        
        success = False
        
        # テスト用のランダムアイコンを取得
        test_icon_path = self.get_random_completion_icon()
        
        # 1. Windowsバルーン通知（最も確実、ランダムアイコン付き）
        if not success:
            self.text_edit.add_log("🔄 Windowsバルーン通知を試行中...")
            success = self.show_windows_balloon_notification(title, message, test_icon_path)
            if success:
                self.text_edit.add_log("✅ Windowsバルーン通知が成功しました")
        
        # 2. QSystemTrayIcon（PyQt5標準）
        if not success:
            self.text_edit.add_log("🔄 PyQt5システムトレイ通知を試行中...")
            success = self.show_system_notification(title, message, duration=8000)
            if success:
                self.text_edit.add_log("✅ PyQt5通知が成功しました")
        
        if success:
            self.text_edit.add_log("✓ テスト通知を送信しました（Windowsの右下を確認してください）")
        else:
            self.text_edit.add_log("⚠ すべてのテスト通知方法が失敗しました")
    
    def init_system_tray(self):
        """システムトレイアイコンを初期化（通知機能用）"""
        try:
            # システムトレイが利用可能かチェック
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.text_edit.add_log("⚠ システムトレイが利用できません")
                self.tray_icon = None
                return
            
            # トレイアイコンを作成
            self.tray_icon = QSystemTrayIcon(self)
            
            # アプリケーションのアイコンを取得（通知アイコンとしても使用）
            self.notification_icon_path = None
            
            # EXE環境でのリソースパス取得関数
            def get_resource_path(relative_path):
                """EXE環境とスクリプト環境の両方でリソースパスを取得"""
                if hasattr(sys, '_MEIPASS'):
                    # PyInstallerでパッケージ化された環境
                    return os.path.join(sys._MEIPASS, relative_path)
                else:
                    # 通常のPythonスクリプト環境
                    return relative_path
            
            # app.icoを優先的に検索（PyInstallerのリソースパスを考慮）
            priority_paths = ['icon/app.ico', 'app.ico']
            
            app_icon_path = None
            for relative_path in priority_paths:
                path = get_resource_path(relative_path)
                if os.path.exists(path):
                    app_icon_path = path
                    self.text_edit.add_log(f"📁 アイコンファイルを発見: {path}")
                    break
                else:
                    self.text_edit.add_log(f"🔍 アイコン検索: {path} (見つからず)")
            
            if app_icon_path:
                # アイコンファイルが存在する場合
                icon = QIcon(app_icon_path)
                self.tray_icon.setIcon(icon)
                self.notification_icon_path = app_icon_path
                self.text_edit.add_log("✓ システムトレイアイコンを初期化しました（app.ico使用）")
            else:
                # デフォルトアイコンを使用
                default_icon = self.style().standardIcon(self.style().SP_ComputerIcon)
                self.tray_icon.setIcon(default_icon)
                self.text_edit.add_log("✓ システムトレイアイコンを初期化しました（デフォルトアイコン）")
                
            # トレイアイコンのツールチップ（これは通知名に影響しないはず）
            self.tray_icon.setToolTip("ClipItBro")
            
            # トレイアイコンを表示（重要！）
            self.tray_icon.show()
            self.text_edit.add_log("✓ システムトレイアイコンを表示しました")
            
            # Windows APIで通知アプリ名を明示的に設定を試行
            self.try_set_notification_app_name()
            
        except Exception as e:
            self.text_edit.add_log(f"⚠ システムトレイアイコンの初期化に失敗: {e}")
            self.tray_icon = None
            self.notification_icon_path = None
    
    def try_set_notification_app_name(self):
        """Windows APIを使用してアプリケーション名とアイコンを明示的に設定を試行"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # SetCurrentProcessExplicitAppUserModelIDを使用してアプリID設定
            shell32 = ctypes.windll.shell32
            shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
            shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
            
            # アプリID設定（通知名に影響する可能性）
            app_id = "ClipItBro"
            result = shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            
            if result == 0:  # S_OK
                self.text_edit.add_log("✓ Windows APIでアプリケーションIDを設定しました")
                
                # 追加: Windowsレジストリにアプリケーション情報を登録
                self.register_app_in_windows()
            else:
                self.text_edit.add_log(f"⚠ Windows APIアプリケーションID設定に失敗: {result}")
            
            # 追加: アプリケーションアイコンをWindowsに登録
            if hasattr(self, 'notification_icon_path') and self.notification_icon_path:
                self.try_register_app_icon()
                
        except Exception as e:
            self.text_edit.add_log(f"📝 Windows APIアプリケーションID設定をスキップ: {e}")
    
    def register_app_in_windows(self):
        """Windowsレジストリにアプリケーション情報を登録"""
        try:
            import winreg
            
            app_id = "ClipItBro"
            app_name = "ClipItBro"
            
            # アプリケーション情報を登録
            app_key_path = f"SOFTWARE\\Classes\\AppUserModelId\\{app_id}"
            
            # HKEY_CURRENT_USERに登録（管理者権限不要）
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, app_key_path) as key:
                # アプリケーション表示名
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, app_name)
                
                # アイコンパスを登録
                if hasattr(self, 'notification_icon_path') and self.notification_icon_path:
                    icon_path = os.path.abspath(self.notification_icon_path)
                    winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, icon_path)
                    self.text_edit.add_log(f"✓ レジストリにアイコンパスを登録: {icon_path}")
                
                # 通知設定
                winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, 1)
                
            self.text_edit.add_log("✓ Windowsレジストリにアプリケーション情報を登録しました")
            
        except Exception as e:
            self.text_edit.add_log(f"📝 Windowsレジストリ登録をスキップ: {e}")
    
    def try_register_app_icon(self):
        """Windowsにアプリケーションアイコンを登録"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # ウィンドウハンドルを取得
            hwnd = int(self.winId())
            
            # アイコンを読み込み
            if self.notification_icon_path and os.path.exists(self.notification_icon_path):
                # LoadImageを使用してアイコンを読み込み
                user32 = ctypes.windll.user32
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                LR_DEFAULTSIZE = 0x00000040
                
                hicon = user32.LoadImageW(
                    None,
                    self.notification_icon_path,
                    IMAGE_ICON,
                    0, 0,
                    LR_LOADFROMFILE | LR_DEFAULTSIZE
                )
                
                if hicon:
                    # ウィンドウアイコンを設定（大・小両方）
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
                    
                    self.text_edit.add_log("✓ Windowsにアプリケーションアイコンを登録しました")
                else:
                    self.text_edit.add_log("⚠ アイコンファイルの読み込みに失敗")
            
        except Exception as e:
            self.text_edit.add_log(f"📝 Windowsアイコン登録をスキップ: {e}")
    
    def show_system_notification(self, title, message, duration=5000):
        """Windowsシステム通知を表示"""
        try:
            self.text_edit.add_log(f"🔍 通知表示を試行中: {title}")
            
            # システムトレイの状態をチェック
            if not self.tray_icon:
                self.text_edit.add_log("⚠ システムトレイアイコンが初期化されていません")
                return False
                
            if not QSystemTrayIcon.isSystemTrayAvailable():
                self.text_edit.add_log("⚠ システムトレイが利用できません")
                return False
            
            if not self.tray_icon.isVisible():
                self.text_edit.add_log("⚠ システムトレイアイコンが非表示です - 再表示を試行")
                self.tray_icon.show()
            
            # 通知がサポートされているかチェック
            if not self.tray_icon.supportsMessages():
                self.text_edit.add_log("⚠ システムトレイが通知メッセージをサポートしていません")
                return False
            
            # システムトレイ経由で通知表示
            self.text_edit.add_log(f"� 通知を送信中: タイトル='{title}', メッセージ='{message[:50]}...', 時間={duration}ms")
            
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.NoIcon,
                duration
            )
            
            self.text_edit.add_log(f"✅ システム通知を送信しました: {title}")
            self.text_edit.add_log("📍 Windowsの右下（通知エリア）を確認してください")
            return True
                
        except Exception as e:
            self.text_edit.add_log(f"❌ システム通知の表示に失敗: {e}")
            import traceback
            self.text_edit.add_log(f"詳細エラー: {traceback.format_exc()}")
            return False
    

    

    

    
    def show_windows_balloon_notification(self, title, message, custom_icon_path=None):
        """Windowsバルーン通知を使用した確実な通知（システムトレイ経由）"""
        try:
            if not self.tray_icon or not self.tray_icon.isVisible():
                self.text_edit.add_log("⚠ システムトレイアイコンが利用できません")
                return False
            
            self.text_edit.add_log("🎈 Windowsバルーン通知を表示します")
            
            # カスタムアイコンパスが指定されている場合はそれを使用
            if custom_icon_path and os.path.exists(custom_icon_path):
                try:
                    icon = QIcon(custom_icon_path)
                    self.tray_icon.showMessage(title, message, icon, 10000)
                    self.text_edit.add_log(f"ランダムアイコンで通知表示: {os.path.basename(custom_icon_path)}")
                except Exception as e:
                    self.text_edit.add_log(f"カスタムアイコン読み込みエラー: {e}")
                    self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 10000)
            # 既存のnotification_icon_pathがあれば使用
            elif hasattr(self, 'notification_icon_path') and self.notification_icon_path and os.path.exists(self.notification_icon_path):
                icon = QIcon(self.notification_icon_path)
                self.tray_icon.showMessage(title, message, icon, 10000)
            else:
                self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 10000)
            
            self.text_edit.add_log("✅ バルーン通知を送信しました")
            return True
            
        except Exception as e:
            self.text_edit.add_log(f"❌ バルーン通知エラー: {e}")
            # フォールバック: アイコンパラメータを省略
            try:
                self.tray_icon.showMessage(title, message)
                return True
            except:
                return False
    
    def show_conversion_completion_notification(self, output_path, clipboard_copied, custom_icon_path=None):
        """変換完了時のシステム通知を表示（画像付き）"""
        try:
            file_name = os.path.basename(output_path)
            
            # ファイルサイズを取得
            try:
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                size_text = f"{file_size:.1f} MB"
            except:
                size_text = ""
            
            # 通知のタイトルとメッセージを作成
            title = f"🎬 変換完了 【{size_text}】"
            
            if clipboard_copied:
                message = f"📋️ 動画をクリップボードにコピーしました\n🗂️ 動画を {os.path.dirname(output_path)} に保存しました"
            else:
                message = f"🗂️ 動画を {os.path.dirname(output_path)} に保存しました"
            
            # 複数の通知システムを順番に試行（確実性を優先）
            success = False
            
            # 1. Windowsバルーン通知（最も確実、カスタムアイコン付き）
            if not success:
                success = self.show_windows_balloon_notification(title, message, custom_icon_path)
                if success:
                    self.text_edit.add_log("✅ バルーン変換完了通知を表示しました")
            
            # 2. PyQt5システムトレイ通知
            if not success:
                self.text_edit.add_log("🔄 PyQt5システムトレイ通知を表示します")
                success = self.show_system_notification(title, message, duration=10000)
                if success:
                    self.text_edit.add_log("✅ PyQt5変換完了通知を表示しました")
            
            # さらに失敗した場合はシンプルな通知
            if not success:
                self.text_edit.add_log("🔄 アイコン付き通知も失敗、シンプル通知を試行します")
                if self.tray_icon:
                    try:
                        self.tray_icon.showMessage(title, message, QSystemTrayIcon.NoIcon, 10000)
                        success = True
                        self.text_edit.add_log("✅ シンプル通知を表示しました")
                    except Exception as e:
                        self.text_edit.add_log(f"❌ シンプル通知も失敗: {e}")
            
            if success:
                self.text_edit.add_log(f"📢 変換完了通知を表示しました: {file_name}")
            else:
                self.text_edit.add_log("⚠ 変換完了通知の表示に失敗しました")
                
        except Exception as e:
            self.text_edit.add_log(f"⚠ 変換完了通知の生成に失敗: {e}")
    
    def change_theme(self, theme_type):
        """テーマを変更"""
        if theme_type == 'dark':
            self.current_theme = ThemeManager.DARK_THEME
        else:
            self.current_theme = ThemeManager.LIGHT_THEME
        
        # テーマを適用
        self.apply_theme()
        
        # メニューの選択状態を更新
        for action in self.theme_group.actions():
            if theme_type == 'dark' and 'ダーク' in action.text():
                action.setChecked(True)
            elif theme_type == 'light' and 'ライト' in action.text():
                action.setChecked(True)
        
        # 設定を保存
        self.save_theme_setting()
        
        # チェックマーク表示を更新
        self.update_menu_checkmarks()
        
        # アプリケーション全体を再描画
        self.update()
        QApplication.processEvents()
    
    def apply_theme(self):
        """現在のテーマを適用"""
        # メインスタイルシートを適用
        stylesheet = ThemeManager.get_stylesheet(self.current_theme)
        self.setStyleSheet(stylesheet)
        
        # 個別ウィジェットに強制的にテーマを適用
        ThemeManager.apply_theme_to_widget(self.text_edit, self.current_theme)
        ThemeManager.apply_theme_to_widget(self.info_label, self.current_theme)
        ThemeManager.apply_theme_to_widget(self.convert_button, self.current_theme)
        ThemeManager.apply_theme_to_widget(self.single_progress_bar, self.current_theme)
        ThemeManager.apply_theme_to_widget(self.pass1_progress_bar, self.current_theme)
        ThemeManager.apply_theme_to_widget(self.pass2_progress_bar, self.current_theme)
        ThemeManager.apply_theme_to_widget(self.mode_button, self.current_theme)
        
        # タイトルバーのテーマも適用
        self.apply_titlebar_theme()
        
        # H.265警告バーの色をテーマに合わせて更新
        self.update_h265_warning_bar()
        
        # 現在の状態に応じた背景色を復元
        if hasattr(self, 'current_status') and self.current_status != 'default':
            ThemeManager.apply_status_background(self.text_edit, self.current_theme, self.current_status)
        
        # テキストエリアの表示を更新
        if hasattr(self.text_edit, 'update_display'):
            self.text_edit.update_display()
    
    def apply_titlebar_theme(self):
        """タイトルバーのテーマを適用"""
        try:
            window_handle = self.winId()
            is_dark = self.current_theme['name'] == 'Dark'
            
            success = set_titlebar_theme(window_handle, is_dark)
            if success:
                theme_name = "ダーク" if is_dark else "ライト"
                print(f"タイトルバーテーマを{theme_name}に設定しました")
            else:
                print("タイトルバーテーマの設定に失敗しました（この環境では対応していない可能性があります）")
        except Exception as e:
            print(f"タイトルバーテーマ設定中にエラー: {e}")

    # === アップデート確認関連メソッド ===
    
    def start_update_check(self):
        """アップデート確認を開始"""
        try:
            self.text_edit.add_log("アップデート確認を開始...")
            self.update_checker = UpdateChecker(APP_VERSION)
            self.update_checker.update_available_signal.connect(self.on_update_available)
            self.update_checker.update_check_failed_signal.connect(self.on_update_check_failed)
            self.update_checker.unreleased_version_signal.connect(self.on_unreleased_version)
            self.update_checker.up_to_date_signal.connect(self.on_up_to_date)
            self.update_checker.start()
        except Exception as e:
            self.text_edit.add_log(f"アップデート確認開始エラー: {e}")
    
    def on_update_available(self, latest_version):
        """アップデートが利用可能な場合の処理"""
        self.update_available = True
        self.latest_version = latest_version
        # リリースノートも保存
        if hasattr(self.update_checker, 'release_notes'):
            self.release_notes = self.update_checker.release_notes
        else:
            self.release_notes = None
        self.update_menu_action.setVisible(True)
        self.text_edit.add_log(f"🔔 新しいバージョン {latest_version} が利用可能です！")
        
        # システムトレイ通知（利用可能な場合）
        if hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "ClipItBro - アップデート通知",
                f"新しいバージョン {latest_version} が利用可能です！\nメニューバーの「アップデートがあります！」をクリックしてください。",
                QSystemTrayIcon.Information,
                5000
            )
    
    def on_update_check_failed(self, error_message):
        """アップデート確認失敗時の処理"""
        self.text_edit.add_log(f"アップデート確認失敗: {error_message}")
    
    def on_unreleased_version(self, released_version):
        """未公開バージョンの場合の処理"""
        self.is_unreleased_version = True
        self.released_version = released_version
        self.update_menu_action.setText('📋 未公開バージョン')
        self.update_menu_action.setVisible(True)
        self.text_edit.add_log(f"📋 未公開バージョンを使用中 (リリース版: {released_version})")
        
        # システムトレイ通知（利用可能な場合）
        if hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "ClipItBro - バージョン情報",
                f"未公開バージョンを使用中です！\n現在: {APP_VERSION}\nリリース版: {released_version}",
                QSystemTrayIcon.Information,
                5000
            )
    
    def on_up_to_date(self):
        """最新バージョンの場合の処理"""
        self.text_edit.add_log(f"✅ 最新バージョンです！ (v{APP_VERSION})")
    
    def show_update_dialog(self):
        """アップデート通知ダイアログを表示"""
        msg_box = QMessageBox(self)
        
        if self.is_unreleased_version:
            # 未公開バージョンの場合
            msg_box.setWindowTitle("バージョン情報")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("未公開バージョンを使用中です！")
            msg_box.setInformativeText(
                f"現在のバージョン: {APP_VERSION} (未公開)\n"
                f"最新リリース版: {self.released_version}\n\n"
                f"開発版やベータ版をお使いいただき、ありがとうございます！\n"
                f"問題がございましたら、GitHubでご報告ください。"
            )
            
            # ボタンをカスタマイズ
            github_button = msg_box.addButton("GitHubで報告", QMessageBox.AcceptRole)
            close_button = msg_box.addButton("閉じる", QMessageBox.RejectRole)
            
        elif self.update_available and self.latest_version:
            # アップデートが利用可能な場合
            msg_box.setWindowTitle("アップデート通知")
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("新しいバージョンが利用可能です！")
            
            # リリースノートがある場合は表示
            info_text = f"現在のバージョン: {APP_VERSION}\n最新バージョン: {self.latest_version}\n\n"
            
            if hasattr(self, 'release_notes') and self.release_notes:
                info_text += f"アップデート内容:\n{self.release_notes}\n\n"
            
            info_text += "自動アップデートを実行しますか？"
            
            msg_box.setInformativeText(info_text)
            
            # ボタンをカスタマイズ
            auto_update_button = msg_box.addButton("自動アップデート", QMessageBox.AcceptRole)
            github_button = msg_box.addButton("GitHubで確認", QMessageBox.ActionRole)
            close_button = msg_box.addButton("後で", QMessageBox.RejectRole)
        else:
            # エラーの場合
            return
        
        # 個別ボタンにテーマを適用（変換完了ウィンドウと同じ方式）
        if self.is_unreleased_version:
            ThemeManager.apply_theme_to_widget(github_button, self.current_theme)
            ThemeManager.apply_theme_to_widget(close_button, self.current_theme)
        elif self.update_available and self.latest_version:
            ThemeManager.apply_theme_to_widget(auto_update_button, self.current_theme)
            ThemeManager.apply_theme_to_widget(github_button, self.current_theme)
            ThemeManager.apply_theme_to_widget(close_button, self.current_theme)
        
        # テーマを適用
        msg_box_style = f"""
        QMessageBox {{
            background-color: {self.current_theme['main_bg']};
            color: {self.current_theme['text_color']};
        }}
        QMessageBox QLabel {{
            color: {self.current_theme['text_color']};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {self.current_theme['button_bg']} !important;
            color: {self.current_theme['button_text']} !important;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
            min-width: auto;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        """
        msg_box.setStyleSheet(msg_box_style)
        
        msg_box.exec_()
        
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == github_button:
            # GitHubページを開く
            try:
                if self.is_unreleased_version:
                    webbrowser.open("https://github.com/EpicJunriel/KIK-ClipItBro/issues")
                    self.text_edit.add_log("GitHubイシューページを開きました")
                else:
                    webbrowser.open("https://github.com/EpicJunriel/KIK-ClipItBro/releases")
                    self.text_edit.add_log("GitHubリリースページを開きました")
            except Exception as e:
                self.text_edit.add_log(f"ブラウザ起動エラー: {e}")
        elif 'auto_update_button' in locals() and clicked_button == auto_update_button:
            # 自動アップデートを実行
            self.start_auto_update()
    
    def start_auto_update(self):
        """自動アップデートを開始"""
        if not self.latest_version:
            self.text_edit.add_log("エラー: 最新バージョン情報が取得できていません")
            return
        
        try:
            self.text_edit.add_log(f"🚀 自動アップデートを開始します...")
            self.text_edit.add_log(f"対象バージョン: {self.latest_version}")
            
            # 一時保存先
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller環境：実行ファイルと同じディレクトリ
                temp_dir = os.path.join(os.path.dirname(sys.executable), "temp_update")
            else:
                # 開発環境：スクリプトと同じディレクトリ
                temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_update")
            
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, f"ClipItBro_{self.latest_version}.exe")
            
            # ダウンローダーを初期化（バージョンと保存先を指定）
            self.update_downloader = UpdateDownloader(self.latest_version, temp_file_path)
            self.update_downloader.download_progress_signal.connect(self.on_download_progress)
            self.update_downloader.download_finished_signal.connect(self.on_download_finished)
            self.update_downloader.download_error_signal.connect(self.on_download_error)
            
            # ダウンロード開始
            self.update_downloader.start()
            
            # プログレスバーを表示
            self.show_download_progress_dialog()
            
        except Exception as e:
            self.text_edit.add_log(f"自動アップデート開始エラー: {e}")
    
    def show_download_progress_dialog(self):
        """ダウンロード進捗ダイアログを表示"""
        self.download_dialog = QDialog(self)
        self.download_dialog.setWindowTitle("アップデートダウンロード中")
        self.download_dialog.setModal(True)
        self.download_dialog.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        # メッセージラベル
        self.download_label = QLabel(f"バージョン {self.latest_version} をダウンロード中...")
        layout.addWidget(self.download_label)
        
        # プログレスバー
        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        layout.addWidget(self.download_progress)
        
        # キャンセルボタン
        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.cancel_download)
        layout.addWidget(cancel_button)
        
        self.download_dialog.setLayout(layout)
        
        # 個別ボタンにテーマを適用（変換完了ウィンドウと同じ方式）
        ThemeManager.apply_theme_to_widget(cancel_button, self.current_theme)
        
        # テーマ適用
        ThemeManager.apply_theme_to_widget(self.download_dialog, self.current_theme)
        
        self.download_dialog.show()
    
    def on_download_progress(self, progress):
        """ダウンロード進捗更新"""
        if hasattr(self, 'download_progress'):
            self.download_progress.setValue(progress)
            self.download_label.setText(f"バージョン {self.latest_version} をダウンロード中... ({progress}%)")
    
    def on_download_finished(self, file_path):
        """ダウンロード完了時の処理"""
        self.text_edit.add_log(f"✓ ダウンロード完了: {file_path}")
        
        # ダウンロードダイアログを閉じる
        if hasattr(self, 'download_dialog'):
            self.download_dialog.close()
        
        # 即座にアップデートを実行
        self.execute_update(file_path)
    
    def on_download_error(self, error_message):
        """ダウンロードエラー時の処理"""
        self.text_edit.add_log(f"✗ ダウンロードエラー: {error_message}")
        
        # ダウンロードダイアログを閉じる
        if hasattr(self, 'download_dialog'):
            self.download_dialog.close()
        
        # エラーダイアログ表示
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("ダウンロードエラー")
        msg_box.setText("アップデートファイルのダウンロードに失敗しました")
        msg_box.setInformativeText(f"エラー詳細: {error_message}")
        
        # テーマを適用
        msg_box_style = f"""
        QMessageBox {{
            background-color: {self.current_theme['main_bg']};
            color: {self.current_theme['text_color']};
        }}
        QMessageBox QLabel {{
            color: {self.current_theme['text_color']};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {self.current_theme['button_bg']} !important;
            color: {self.current_theme['button_text']} !important;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
            min-width: auto;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        """
        msg_box.setStyleSheet(msg_box_style)
        msg_box.exec_()
    
    def cancel_download(self):
        """ダウンロードをキャンセル"""
        if hasattr(self, 'update_downloader'):
            self.update_downloader.cancel_download()
        
        if hasattr(self, 'download_dialog'):
            self.download_dialog.close()
        
        self.text_edit.add_log("ダウンロードをキャンセルしました")
    
    def confirm_and_execute_update(self, new_exe_path):
        """アップデート実行の最終確認"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("アップデート実行確認")
        msg_box.setText("アップデートを実行しますか？")
        msg_box.setInformativeText(
            f"新しいバージョン ({self.latest_version}) のダウンロードが完了しました。\n\n"
            f"アップデートを実行すると、アプリケーションが終了されます。\n"
            f"現在の作業内容は保存されません。"
        )
        
        execute_button = msg_box.addButton("実行", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("後で", QMessageBox.RejectRole)
        
        # 個別ボタンにテーマを適用（変換完了ウィンドウと同じ方式）
        ThemeManager.apply_theme_to_widget(execute_button, self.current_theme)
        ThemeManager.apply_theme_to_widget(cancel_button, self.current_theme)
        
        # テーマを適用
        msg_box_style = f"""
        QMessageBox {{
            background-color: {self.current_theme['main_bg']};
            color: {self.current_theme['text_color']};
        }}
        QMessageBox QLabel {{
            color: {self.current_theme['text_color']};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            background-color: {self.current_theme['button_bg']} !important;
            color: {self.current_theme['button_text']} !important;
            border: none;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
            min-width: auto;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {self.current_theme['button_hover']} !important;
        }}
        """
        msg_box.setStyleSheet(msg_box_style)
        msg_box.exec_()
        
        if msg_box.clickedButton() == execute_button:
            self.execute_update(new_exe_path)
        else:
            self.text_edit.add_log("アップデートを後回しにしました")
            self.text_edit.add_log(f"ダウンロード済みファイル: {new_exe_path}")
    
    def execute_update(self, new_exe_path):
        """アップデートを実行"""
        try:
            self.text_edit.add_log("🔄 アップデートを実行中...")
            self.text_edit.add_log(f"新しいexe: {new_exe_path}")
            
            # updater.batの利用可能性をチェック
            if not UpdateManager.check_updater_availability():
                self.text_edit.add_log("✗ updater.batが見つかりません")
                # フォールバック：レガシーな方法を使用
                current_exe_path = sys.executable
                if UpdateManager.execute_update(current_exe_path, new_exe_path, restart=True):
                    self.text_edit.add_log("✓ レガシーアップデート方式を使用しました")
                    QTimer.singleShot(1000, QApplication.quit)
                else:
                    self.text_edit.add_log("✗ アップデート実行に失敗しました")
                return
            
            # updater.batを使用してアップデート実行
            if UpdateManager.execute_update_with_batch(new_exe_path):
                self.text_edit.add_log("✓ updater.batを実行しました")
                self.text_edit.add_log("アプリケーションを終了します...")
                
                # アプリケーションを終了
                QTimer.singleShot(1000, QApplication.quit)
            else:
                self.text_edit.add_log("✗ updater.bat実行に失敗しました")
                
        except Exception as e:
            self.text_edit.add_log(f"アップデート実行エラー: {e}")

# 非同期変換処理用のスレッドクラス
class ConversionThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(float)  # 進行状況シグナル
    finished_signal = pyqtSignal(bool, str, str)  # success, output_path, error_message
    
    def __init__(self, cmd, env, output_path, total_duration):
        super().__init__()
        self.cmd = cmd
        self.env = env
        self.output_path = output_path
        self.total_duration = total_duration
    
    def run(self):
        try:
            self.log_signal.emit(f"実行コマンド: {' '.join(self.cmd)}")
            
            # FFmpegをリアルタイム監視で実行
            import re
            
            # Windowsでコマンドプロンプトウィンドウを表示しないための設定
            startupinfo = None
            if os.name == 'nt':  # Windows環境の場合
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # stderrもstdoutにリダイレクト
                text=True,
                env=self.env,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True,
                startupinfo=startupinfo,  # ウィンドウ非表示設定を追加
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0  # 追加の非表示フラグ
            )
            
            current_time = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # FFmpegの進行状況を解析（time=00:01:23.45形式）
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', output)
                    if time_match and self.total_duration > 0:
                        hours = int(time_match.group(1))
                        minutes = int(time_match.group(2))
                        seconds = int(time_match.group(3))
                        centiseconds = int(time_match.group(4))
                        
                        current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        progress_percent = min(100, (current_time / self.total_duration) * 100)
                        self.progress_signal.emit(progress_percent)
                        
                        # 進行状況をログに出力（頻度を制限）
                        if int(progress_percent) % 10 == 0:  # 10%ごとにログ出力
                            self.log_signal.emit(f"変換進行状況: {progress_percent:.1f}%")
            
            # プロセス終了を待機
            return_code = process.wait()
            
            if return_code == 0:
                self.progress_signal.emit(100)  # 完了時は100%
                self.log_signal.emit("FFmpeg実行成功")
                self.finished_signal.emit(True, self.output_path, "")
            else:
                self.log_signal.emit(f"FFmpeg実行失敗: 終了コード {return_code}")
                self.finished_signal.emit(False, self.output_path, f"終了コード: {return_code}")
                
        except Exception as e:
            self.log_signal.emit(f"変換処理エラー: {e}")
            self.finished_signal.emit(False, self.output_path, str(e))

# 1pass目解析用のスレッドクラス
class FirstPassThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(float)  # 進行状況シグナルを追加
    finished_signal = pyqtSignal(bool, str, str)  # success, log_file_path, error_message
    
    def __init__(self, video_file_path, temp_bitrate, total_duration=0, use_h265=False):
        super().__init__()
        self.video_file_path = video_file_path
        self.temp_bitrate = temp_bitrate
        self.total_duration = total_duration  # 動画の総時間を追加
        self.use_h265 = use_h265
        self.process = None  # プロセス参照を保持
        self._should_stop = False  # 停止フラグ
    
    def stop(self):
        """スレッドを停止"""
        self._should_stop = True
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
    
    def run(self):
        try:
            ffmpeg_path = get_ffmpeg_executable_path('ffmpeg.exe')
            
            # 1pass目用のログファイル名を生成
            # 1pass目のコマンド構築
            # コーデック選択
            codec = 'libx265' if self.use_h265 else 'libx264'
            
            cmd = [
                ffmpeg_path,
                '-y',  # ファイル上書き許可
                '-i', self.video_file_path,
                '-c:v', codec,
                '-b:v', f'{self.temp_bitrate}k',
                '-pass', '1',
                '-f', 'null'
            ]
            
            # Windowsの場合はNULデバイスを指定
            if os.name == 'nt':
                cmd.append('NUL')
            else:
                cmd.append('/dev/null')
            
            self.log_signal.emit(f"1pass実行: {os.path.basename(self.video_file_path)}")
            
            # 環境変数設定
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            if os.name == 'nt':
                env['LANG'] = 'ja_JP.UTF-8'
            
            # 1pass目を実行
            import re
            
            # Windowsでコマンドプロンプトウィンドウを表示しないための設定
            startupinfo = None
            if os.name == 'nt':  # Windows環境の場合
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True,
                startupinfo=startupinfo,  # ウィンドウ非表示設定を追加
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0  # 追加の非表示フラグ
            )
            
            # 出力を監視してプログレスを解析
            current_time = 0
            while True:
                if self._should_stop:  # 停止要求チェック
                    self.process.terminate()
                    self.finished_signal.emit(False, "", "1pass解析が停止されました")
                    return
                    
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    # FFmpegの進行状況を解析（time=00:01:23.45形式）
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', output)
                    if time_match and self.total_duration > 0:
                        hours = int(time_match.group(1))
                        minutes = int(time_match.group(2))
                        seconds = int(time_match.group(3))
                        centiseconds = int(time_match.group(4))
                        
                        current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        progress_percent = min(100, (current_time / self.total_duration) * 100)
                        self.progress_signal.emit(progress_percent)
                        
                        # 進行状況をログに出力（頻度を制限）
                        if int(progress_percent) % 20 == 0:  # 20%ごとにログ出力
                            self.log_signal.emit(f"1pass進行状況: {progress_percent:.1f}%")
                    
                    # エラーや警告をログ出力
                    if 'error' in output.lower() or 'warning' in output.lower():
                        self.log_signal.emit(f"1pass: {output.strip()}")
            
            if self._should_stop:  # 停止要求の最終チェック
                self.finished_signal.emit(False, "", "1pass解析が停止されました")
                return
                
            return_code = self.process.wait()
            
            if return_code == 0:
                self.progress_signal.emit(100)  # 完了時は100%
                self.log_signal.emit("1pass解析完了")
                self.finished_signal.emit(True, "1pass_analysis_completed", "")
            else:
                self.log_signal.emit(f"1pass解析失敗: 終了コード {return_code}")
                self.finished_signal.emit(False, "", f"終了コード: {return_code}")
                
        except Exception as e:
            self.log_signal.emit(f"1pass解析エラー: {e}")
            self.finished_signal.emit(False, "", str(e))

# 2pass変換用のスレッドクラス（1pass+2passを連続実行）
class TwoPassConversionThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(float)
    phase_signal = pyqtSignal(int)  # 1=1pass目, 2=2pass目
    finished_signal = pyqtSignal(bool, str, str)  # success, output_path, error_message
    
    def __init__(self, video_file_path, output_path, target_bitrate, total_duration, second_pass_only=False, use_h265=False):
        super().__init__()
        self.video_file_path = video_file_path
        self.output_path = output_path
        self.target_bitrate = target_bitrate
        self.total_duration = total_duration
        self.second_pass_only = second_pass_only
        self.use_h265 = use_h265
        
        # 環境変数設定
        self.env = os.environ.copy()
        self.env['PYTHONIOENCODING'] = 'utf-8'
        if os.name == 'nt':
            self.env['LANG'] = 'ja_JP.UTF-8'
    
    def run(self):
        try:
            ffmpeg_path = get_ffmpeg_executable_path('ffmpeg.exe')
            
            if not self.second_pass_only:
                # === 1pass目実行 ===
                self.phase_signal.emit(1)
                self.log_signal.emit("=== 1pass目開始 ===")
                
                # コーデック選択
                video_codec = 'libx265' if self.use_h265 else 'libx264'
                codec_name = 'H.265 (HEVC)' if self.use_h265 else 'H.264 (x264)'
                self.log_signal.emit(f"📹 使用コーデック: {codec_name}")
                
                cmd1 = [
                    ffmpeg_path,
                    '-y',
                    '-i', self.video_file_path,
                    '-c:v', video_codec,
                    '-b:v', f'{self.target_bitrate}k',
                    '-pass', '1',
                    '-f', 'null'
                ]
                
                if os.name == 'nt':
                    cmd1.append('NUL')
                else:
                    cmd1.append('/dev/null')
                
                # 1pass目実行
                if not self.execute_pass(cmd1, 1):
                    return
            
            # === 2pass目実行 ===
            self.phase_signal.emit(2)
            self.log_signal.emit("=== 2pass目開始 ===")
            
            # コーデック選択（2pass目でも同じコーデックを使用）
            video_codec = 'libx265' if self.use_h265 else 'libx264'
            
            cmd2 = [
                ffmpeg_path,
                '-y',
                '-i', self.video_file_path,
                '-c:v', video_codec,
                '-b:v', f'{self.target_bitrate}k',
                '-pass', '2',
                '-c:a', 'aac',
                '-b:a', '128k',
                self.output_path
            ]
            
            # 2pass目実行
            if not self.execute_pass(cmd2, 2):
                return
            
            self.log_signal.emit("2pass変換完了")
            self.finished_signal.emit(True, self.output_path, "")
            
        except Exception as e:
            self.log_signal.emit(f"2pass変換エラー: {e}")
            self.finished_signal.emit(False, self.output_path, str(e))
    
    def execute_pass(self, cmd, pass_number):
        """指定されたpassを実行"""
        try:
            import re
            
            # Windowsでコマンドプロンプトウィンドウを表示しないための設定
            startupinfo = None
            if os.name == 'nt':  # Windows環境の場合
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True,
                startupinfo=startupinfo,  # ウィンドウ非表示設定を追加
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0  # 追加の非表示フラグ
            )
            
            current_time = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # FFmpegの進行状況を解析（time=00:01:23.45形式）
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', output)
                    if time_match and self.total_duration > 0:
                        hours = int(time_match.group(1))
                        minutes = int(time_match.group(2))
                        seconds = int(time_match.group(3))
                        centiseconds = int(time_match.group(4))
                        
                        current_time = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
                        
                        # 各パスごとに0-100%で計算し、全体の進行度に変換
                        pass_progress = min(100, (current_time / self.total_duration) * 100)
                        
                        if pass_number == 1:
                            # 1pass目: 0-50%
                            progress_percent = pass_progress * 0.5
                        else:
                            # 2pass目: 50-100%
                            progress_percent = 50 + (pass_progress * 0.5)
                        
                        self.progress_signal.emit(progress_percent)
                        
                        # 進行状況をログに出力（頻度を制限）
                        if int(pass_progress) % 20 == 0:
                            self.log_signal.emit(f"{pass_number}pass進行状況: {pass_progress:.1f}% (全体: {progress_percent:.1f}%)")
            
            return_code = process.wait()
            
            if return_code == 0:
                self.log_signal.emit(f"{pass_number}pass目完了")
                return True
            else:
                self.log_signal.emit(f"{pass_number}pass目失敗: 終了コード {return_code}")
                self.finished_signal.emit(False, self.output_path, f"{pass_number}pass目失敗: 終了コード {return_code}")
                return False
                
        except Exception as e:
            self.log_signal.emit(f"{pass_number}pass目エラー: {e}")
            self.finished_signal.emit(False, self.output_path, str(e))
            return False

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(None)  # 親をNoneに設定してタイトル自動追加を防ぐ
        self.parent_window = parent
        self.setWindowTitle("ClipItBro について")
        self.setFixedSize(700, 400)  # ダイアログサイズをさらに拡大
        self.setWindowIcon(self.get_app_icon())
        
        # ウィンドウフラグを設定してクエスチョンマークボタンを削除し、独立したダイアログとして表示
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)
        
        # メインレイアウト（水平分割）
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 左側：ロゴエリア
        logo_widget = QWidget()
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setAlignment(Qt.AlignCenter)
        logo_layout.setContentsMargins(15, 15, 15, 15)
        
        # ロゴ画像
        logo_label = QLabel()
        logo_file_path = self.get_logo_image()
        if logo_file_path:
            # ファイル拡張子をチェック
            if logo_file_path.lower().endswith('.gif'):
                # GIFアニメーションの場合
                self.logo_movie = QMovie(logo_file_path)
                
                # 利用可能スペースを拡大
                available_width = 220  # 160 → 220に拡大
                available_height = 320  # 280 → 320に拡大
                
                # GIFのサイズを取得してスケールファクターを計算
                self.logo_movie.jumpToFrame(0)
                original_size = self.logo_movie.currentPixmap().size()
                
                scale_w = available_width / original_size.width()
                scale_h = available_height / original_size.height()
                scale_factor = min(scale_w, scale_h)
                
                # スケールされたサイズを設定
                scaled_size = original_size * scale_factor
                self.logo_movie.setScaledSize(scaled_size)
                
                logo_label.setMovie(self.logo_movie)
                logo_label.setMinimumSize(available_width, available_height)
                self.logo_movie.start()  # アニメーション開始
            else:
                # 静止画像の場合（PNG, JPG, ICO等）
                logo_pixmap = QPixmap(logo_file_path)
                available_width = 220  # 160 → 220に拡大
                available_height = 320  # 280 → 320に拡大
                
                # アスペクト比を維持しながらフィット
                scaled_pixmap = logo_pixmap.scaled(
                    available_width, available_height, 
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logo_label.setPixmap(scaled_pixmap)
                logo_label.setMinimumSize(available_width, available_height)
        else:
            # ロゴが見つからない場合のフォールバック
            logo_label.setText("🎬")
            logo_label.setStyleSheet("font-size: 80px;")  # 64px → 80pxに拡大
            logo_label.setMinimumSize(220, 320)
        
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setScaledContents(False)  # 自動スケーリングを無効化
        
        logo_layout.addWidget(logo_label)
        # 背景色と枠線を削除してクリーンな表示に
        logo_widget.setStyleSheet("")
        
        # 右側：テキストエリア
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setSpacing(10)  # 20 → 10に縮小
        text_layout.setAlignment(Qt.AlignCenter)  # 上下中央揃えに変更
        text_layout.setContentsMargins(20, 20, 20, 20)
        
        # 上部スペーサー
        text_layout.addStretch()
        
        # タイトル行（アプリ名 + バージョンを横並び）
        title_layout = QHBoxLayout()
        title_layout.setSpacing(4)  # 間隔をより詰める（8→4）
        title_layout.setAlignment(Qt.AlignLeft | Qt.AlignBaseline)  # ベースライン揃え
        
        # アプリケーション名
        app_name = QLabel(APP_NAME)
        app_name.setFont(QFont("Arial", 22, QFont.Bold))
        app_name.setObjectName("app_name")
        
        # バージョン情報
        version_label = QLabel(APP_VERSION)
        version_label.setFont(QFont("Arial", 11))
        version_label.setObjectName("version_label")
        
        # サブタイトル（同じ行に追加）
        subtitle_label = QLabel(f"powered by {APP_DEVELOPER}")
        subtitle_label.setFont(QFont("Arial", 13, QFont.Bold))
        subtitle_label.setObjectName("subtitle_label")
        
        title_layout.addWidget(app_name, 0, Qt.AlignBaseline)  # ベースライン揃え
        title_layout.addWidget(subtitle_label, 0, Qt.AlignBaseline)  # ベースライン揃え
        title_layout.addStretch()  # 右側にスペースを追加
        
        # レイアウトに追加
        text_layout.addLayout(title_layout)
        text_layout.addWidget(version_label, 0, Qt.AlignLeft)  # バージョンを次の行に、左寄せ
        text_layout.setSpacing(2)  # 要素間の間隔を詰める
        
        # 制作者情報
        creator_label = QLabel(f"{APP_DEVELOPER}(KIKUCHIGUMI)は、2020年から本格的な活動を開始した、異能マルチクリエイター集団。アニメ・ゲームカルチャーから影響を受けた独自のクリエイティビティで、多方面での活動を展開している。2025年には新たに三角さこんを迎え、VALORANTシーンにも活動の幅を広めている。")
        creator_label.setFont(QFont("Arial", 11))
        creator_label.setObjectName("creator_label")
        creator_label.setWordWrap(True)
        creator_label.setAlignment(Qt.AlignLeft)

        # コピーライト
        copyright_label = QLabel(f"Built with FFmpeg - https://ffmpeg.org\nFFmpeg is licensed under the LGPL/GPL.\n\n© {APP_COPYRIGHT} {APP_DEVELOPER}. All rights reserved.")
        copyright_label.setFont(QFont("Arial", 9))
        copyright_label.setObjectName("copyright_label")
        copyright_label.setAlignment(Qt.AlignLeft)
        text_layout.addWidget(creator_label)
        text_layout.addWidget(copyright_label)
        
        # 下部スペーサー
        text_layout.addStretch()
        
        # ボタンエリア（水平レイアウト）
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # GitHubアイコン（クリック可能なラベル）
        self.github_icon = QLabel()
        self.github_icon.setObjectName("github_icon")
        self.github_icon.setToolTip("GitHubリポジトリを開く")
        self.github_icon.setCursor(Qt.PointingHandCursor)
        self.github_icon.setAlignment(Qt.AlignCenter)
        
        # GitHubアイコン画像を設定（初期設定）
        self.update_github_icon()
        
        # イベントハンドラを設定
        self.github_icon.mousePressEvent = lambda event: self.open_github() if event.button() == Qt.LeftButton else None
        
        # ホバー効果のためのイベントハンドラ
        def on_enter(event):
            if self.parent_window and hasattr(self.parent_window, 'current_theme'):
                theme = self.parent_window.current_theme
                hover_style = f"background-color: {theme['slider_bg']}; border: 2px solid {theme['border_color']}; border-radius: 6px; padding: 4px;"
                self.github_icon.setStyleSheet(hover_style)
        
        def on_leave(event):
            self.github_icon.setStyleSheet("background-color: transparent; border: 2px solid transparent; border-radius: 6px; padding: 4px;")
        
        self.github_icon.enterEvent = on_enter
        self.github_icon.leaveEvent = on_leave
        
        button_layout.addWidget(self.github_icon)
        
        # スペーサー
        button_layout.addStretch()
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.setObjectName("close_button")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        # ボタンレイアウトをメインレイアウトに追加
        text_layout.addLayout(button_layout)
        
        # メインレイアウトに追加（比率調整）
        main_layout.addWidget(logo_widget, 2)  # 左側の比重を増加
        main_layout.addWidget(text_widget, 3)  # 右側の比重
        
        self.setLayout(main_layout)
        
        # テーマを適用
        self.apply_theme()
    
    def apply_theme(self):
        """親ウィンドウのテーマを適用"""
        if self.parent_window and hasattr(self.parent_window, 'current_theme'):
            theme = self.parent_window.current_theme
        else:
            theme = ThemeManager.LIGHT_THEME
        
        # ダイアログ全体のスタイル
        dialog_style = f"""
            QDialog {{
                background-color: {theme['main_bg']};
                border: 1px solid {theme['border_color']};
                border-radius: 8px;
                color: {theme['text_color']};
            }}
            QLabel#app_name {{
                color: {theme['text_color']};
                margin-bottom: 0px;
                vertical-align: baseline;
            }}
            QLabel#version_label {{
                color: {theme['border_color']};
                margin-bottom: 6px;
                margin-top: 0px;
                vertical-align: top;
            }}
            QLabel#subtitle_label {{
                color: {theme['border_color']};
                margin-top: 6px;
                margin-bottom: 0px;
                vertical-align: baseline;
            }}
            QLabel#creator_label {{
                color: {theme['text_color']};
                line-height: 1.6;
                margin-top: 5px;
                margin-bottom: 5px;
            }}
            QLabel#copyright_label {{
                color: {theme['border_color']};
                font-style: italic;
                margin-top: 12px;
            }}
            QLabel#ffmpeg_credit {{
                color: {theme['border_color']};
                font-size: 8px;
                margin-top: 10px;
                line-height: 1.4;
            }}
            QPushButton#close_button {{
                background-color: {theme['button_bg']};
                color: {theme['button_text']};
                border: 1px solid {theme['border_color']};
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton#close_button:hover {{
                background-color: {theme['button_hover']};
            }}
            QPushButton#close_button:pressed {{
                background-color: {theme['border_color']};
            }}
            QLabel#github_icon {{
                background-color: transparent;
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 4px;
            }}
            QLabel#github_icon:hover {{
                background-color: {theme['slider_bg']};
                border: 2px solid {theme['border_color']};
            }}
        """
        self.setStyleSheet(dialog_style)
        
        # Windowsタイトルバーテーマを設定
        if self.parent_window and hasattr(self.parent_window, 'current_theme'):
            is_dark_mode = self.parent_window.current_theme['name'] == 'Dark'
            set_titlebar_theme(int(self.winId()), is_dark_mode)
        
        # GitHubアイコンもテーマに応じて更新
        self.update_github_icon()
    
    def update_github_icon(self):
        """GitHubアイコンをテーマに応じて更新"""
        github_icon_path = self.get_github_icon()
        if github_icon_path and hasattr(self, 'github_icon'):
            pixmap = QPixmap(github_icon_path)
            # アイコンサイズを調整（32x32ピクセル）
            scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.github_icon.setPixmap(scaled_pixmap)
        elif hasattr(self, 'github_icon'):
            # フォールバック：テキスト表示
            self.github_icon.setText("⭐ GitHub")
            self.github_icon.setStyleSheet("font-size: 14px; padding: 8px;")
    
    def open_github(self):
        """GitHubリポジトリを開く"""
        import webbrowser
        github_url = "https://github.com/EpicJunriel/KIK-ClipItBro"  
        try:
            webbrowser.open(github_url)
        except Exception as e:
            QMessageBox.information(self, "情報", f"ブラウザを開けませんでした。\n手動でアクセスしてください:\n{github_url}")
    
    def get_github_icon(self):
        """GitHubアイコンを取得（テーマ対応・EXE対応）"""
        def get_resource_path(relative_path):
            """EXE環境とスクリプト環境の両方でリソースパスを取得"""
            if hasattr(sys, '_MEIPASS'):
                # PyInstallerでパッケージ化された環境
                return os.path.join(sys._MEIPASS, relative_path)
            else:
                # 通常のPythonスクリプト環境
                return relative_path
        
        # 現在のテーマを取得
        is_dark_theme = False
        if self.parent_window and hasattr(self.parent_window, 'current_theme'):
            is_dark_theme = self.parent_window.current_theme['name'] == 'Dark'
        
        # テーマに応じたGitHubアイコンのパス候補
        if is_dark_theme:
            # ダークテーマ: 白いアイコン
            github_icon_paths = [
                "icon/github/github-mark-white.png",
                "icon/github/github-white.png",
                "icon/github.png",
                "github-white.png"
            ]
        else:
            # ライトテーマ: 黒いアイコン
            github_icon_paths = [
                "icon/github/github-mark.png",
                "icon/github/github-black.png", 
                "icon/github/github.png",
                "github.png"
            ]
        
        for path in github_icon_paths:
            resource_path = get_resource_path(path)
            if os.path.exists(resource_path):
                return resource_path
        return None
    
    def get_app_icon(self):
        """アプリケーションアイコンを取得（EXE対応）"""
        def get_resource_path(relative_path):
            """EXE環境とスクリプト環境の両方でリソースパスを取得"""
            if hasattr(sys, '_MEIPASS'):
                # PyInstallerでパッケージ化された環境
                return os.path.join(sys._MEIPASS, relative_path)
            else:
                # 通常のPythonスクリプト環境
                return relative_path
        
        icon_paths = ["icon/app.ico", "icon/app.png", "app.ico", "app.png"]
        for path in icon_paths:
            resource_path = get_resource_path(path)
            if os.path.exists(resource_path):
                return QIcon(resource_path)
        
        # フォールバック：標準アイコン
        try:
            style = self.style()
            return style.standardIcon(style.SP_ComputerIcon)
        except:
            return QIcon()
    
    def get_logo_image(self):
        """制作者ロゴ画像を取得（GIF対応・EXE対応）"""
        def get_resource_path(relative_path):
            """EXE環境とスクリプト環境の両方でリソースパスを取得"""
            if hasattr(sys, '_MEIPASS'):
                # PyInstallerでパッケージ化された環境
                return os.path.join(sys._MEIPASS, relative_path)
            else:
                # 通常のPythonスクリプト環境
                return relative_path
        
        logo_paths = ["icon/logo.gif", "icon/logo.png", "icon/logo.jpg", "icon/logo.ico", 
                     "logo.gif", "logo.png", "logo.jpg", "logo.ico"]
        for path in logo_paths:
            resource_path = get_resource_path(path)
            if os.path.exists(resource_path):
                return resource_path  # ファイルパスを返す（GIFとPNG/JPGの両方に対応）
        return None

    def showEvent(self, event):
        """ダイアログ表示時にタイトルバーテーマを確実に適用"""
        super().showEvent(event)
        # ダイアログが完全に表示された後にタイトルバーテーマを適用
        if self.parent_window and hasattr(self.parent_window, 'current_theme'):
            is_dark_mode = self.parent_window.current_theme['name'] == 'Dark'
            # 少し遅延させて確実に適用
            QTimer.singleShot(50, lambda: set_titlebar_theme(int(self.winId()), is_dark_mode))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # アプリケーション情報を設定（タスクバー統合のため固定値を使用）
    app.setOrganizationName("KikuchiGumi")
    app.setApplicationName("ClipItBro")
    app.setApplicationVersion(APP_VERSION)
    
    # Windows固有の設定を最優先で実行
    if sys.platform == "win32":
        try:
            import ctypes
            # 固定のAppUserModelIDを設定（バージョンに依存しない）
            # タスクバー固定で使用されるIDと一致させる
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ClipItBro.KikuchiGumi.VideoConverter")
            print("✓ 早期AppUserModelID設定完了")
        except Exception as e:
            print(f"Windows固有設定エラー: {e}")
    
    # EXE環境でのリソースパス取得
    def get_resource_path(relative_path):
        """EXE環境とスクリプト環境の両方でリソースパスを取得"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstallerでパッケージ化された環境
            return os.path.join(sys._MEIPASS, relative_path)
        else:
            # 通常のPythonスクリプト環境
            return relative_path
    
    # アプリケーション全体のアイコンを早期設定
    icon_paths = ["icon/app.ico", "icon/app.png", "app.ico", "app.png"]
    app_icon_set = False
    
    for path in icon_paths:
        resource_path = get_resource_path(path)
        if os.path.exists(resource_path):
            try:
                app_icon = QIcon(resource_path)
                app.setWindowIcon(app_icon)
                app_icon_set = True
                print(f"アプリケーションアイコンを設定: {os.path.basename(resource_path)}")
                break
            except Exception as e:
                print(f"アイコン設定エラー: {e}")
    
    if not app_icon_set:
        print("カスタムアイコンが見つかりません。デフォルトアイコンを使用します。")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
