import sys
import os
import subprocess
import json
import datetime
import platform
import random
import glob
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QProgressBar, QMessageBox, QMenuBar, QAction, QDialog, QMenu, QActionGroup
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QFont, QMovie

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
        }}
        
        QMenu::item {{
            padding: 5px 20px;
        }}
        
        QMenu::item:selected {{
            background-color: {theme['button_bg']};
            color: {theme['button_text']};
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
            content = "ClipItBro v1.0 by 菊池組\n"
            content += "動画ファイル（mp4, avi, mov等）をここにドラッグ&ドロップしてください\n"
            content += "2pass方式では、ドロップ時に自動的に1pass解析を実行します\n\n"

        content += "=== ログ ===\n"
        content += "\n".join(self.log_messages)
        
        self.setText(content)

    def get_video_info(self, file_path):
        """FFprobeを使って動画情報を取得"""
        ffprobe_path = os.path.normpath('bin/ffprobe.exe')
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, 
                                   encoding='utf-8', errors='replace', env=env)
            
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
                        if hasattr(self, '_first_pass_running'):
                            self._first_pass_running = False
                    
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
                                if hasattr(self, '_first_pass_running'):
                                    self._first_pass_running = False
                            
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
                self.first_pass_thread = FirstPassThread(self.video_file_path, temp_bitrate, total_duration)
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
            self.add_log("=== 1pass解析完了 ===")
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
        # MainWindowのドラッグアンドドロップは無効にして、子ウィジェットで処理
        # self.setAcceptDrops(False) を削除
        self.setWindowTitle('ClipItBro by 菊池組')
        self.setGeometry(100, 100, 700, 600)  # サイズを大きくする

        # 設定管理
        self.settings = QSettings('ClipItBro', 'Settings')
        
        # テーマ初期化
        self.current_theme = ThemeManager.LIGHT_THEME
        self.load_theme_setting()
        
        # 状態管理（テーマ変更時の背景色復元用）
        self.current_status = 'default'  # default, success, error, warning, active
        self.ffmpeg_available = False  # FFmpeg利用可能フラグ
        
        # エンコード方式管理
        self.encoding_mode = 'twopass'  # 'twopass' または 'crf'

        # メニューバーを作成
        self.create_menu_bar()

        # メインウィジェットとレイアウト
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)

        # ffmpeg情報表示エリア（ドラッグ＆ドロップ対応）
        self.text_edit = DragDropTextEdit(self)
        main_layout.addWidget(self.text_edit)

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
        self.info_label = QLabel('目標ファイルサイズ: 50 MB | 推定ビットレート: 動画を選択してください', self)
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
        
        # FFmpeg バージョン表示（テーマ適用後）
        self.show_ffmpeg_version()

    def set_application_icon(self):
        # カスタムアイコンファイルを検索（複数の形式をサポート）
        icon_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif']
        custom_icon_path = None
        
        # app.icoを優先的に検索（Windowsの標準）
        priority_paths = ['icon/app.ico', 'app.ico']
        for path in priority_paths:
            if os.path.exists(path):
                custom_icon_path = path
                break
        
        # .icoが見つからない場合は他の形式を検索
        if not custom_icon_path:
            for ext in icon_extensions[1:]:  # .ico以外
                potential_path = f"icon/app{ext}"
                if os.path.exists(potential_path):
                    custom_icon_path = potential_path
                    break
        
        if custom_icon_path:
            try:
                # カスタムアイコンを設定
                app_icon = QIcon(custom_icon_path)
                self.setWindowIcon(app_icon)
                
                # アプリケーション全体のアイコンも設定
                QApplication.instance().setWindowIcon(app_icon)
                
                self.text_edit.add_log(f"アプリケーションアイコンを設定しました: {custom_icon_path}")
            except Exception as e:
                self.text_edit.add_log(f"アプリケーションアイコン設定エラー: {e}")
        else:
            self.text_edit.add_log("カスタムアプリケーションアイコンが見つかりません")

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
                if hasattr(self.text_edit, '_first_pass_running'):
                    self.text_edit._first_pass_running = False
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
        # カスタムアイコンファイルを検索（複数の形式をサポート）
        icon_extensions = ['.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif']
        custom_icon_path = None
        
        # app.icoを優先的に検索（Windowsの標準）
        priority_paths = ['icon/app.ico', 'app.ico']
        for path in priority_paths:
            if os.path.exists(path):
                custom_icon_path = path
                break
        
        # .icoが見つからない場合は他の形式を検索
        if not custom_icon_path:
            for ext in icon_extensions[1:]:  # .ico以外
                potential_path = f"icon/app{ext}"
                if os.path.exists(potential_path):
                    custom_icon_path = potential_path
                    break
        
        if custom_icon_path:
            try:
                # カスタムアイコンを設定
                app_icon = QIcon(custom_icon_path)
                self.setWindowIcon(app_icon)
                
                # アプリケーション全体のアイコンも設定
                QApplication.instance().setWindowIcon(app_icon)
                
                self.text_edit.add_log(f"アプリケーションアイコンを設定しました: {custom_icon_path}")
            except Exception as e:
                self.text_edit.add_log(f"アプリケーションアイコン設定エラー: {e}")
        else:
            self.text_edit.add_log("カスタムアプリケーションアイコンが見つかりません")

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
        
        ffmpeg_path = os.path.normpath('bin/ffmpeg.exe')
        ffprobe_path = os.path.normpath('bin/ffprobe.exe')
        
        # FFmpegのチェック
        try:
            result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True, check=True)
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
            result = subprocess.run([ffprobe_path, '-version'], capture_output=True, text=True, check=True)
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
        
        # 出力ファイル名生成
        input_filename = os.path.basename(video_file)
        name_without_ext = os.path.splitext(input_filename)[0]
        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        
        if self.encoding_mode == 'twopass':
            output_filename = f"ClipItBro_{timestamp}_2pass_{name_without_ext}.mp4"
        else:
            output_filename = f"ClipItBro_{timestamp}_CRF_{name_without_ext}.mp4"
            
        output_path = os.path.join(os.path.dirname(video_file), output_filename)
        
        self.text_edit.add_log(f"=== {self.encoding_mode.upper()}変換開始 ===")
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
                video_file, output_path, target_bitrate, total_duration
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
        ffmpeg_path = os.path.normpath('bin/ffmpeg.exe')
        
        # ログファイル名を取得
        video_dir = os.path.dirname(video_file)
        video_name = os.path.splitext(os.path.basename(video_file))[0]
        log_file = os.path.join(video_dir, f"ffmpeg2pass-{video_name}")
        
        cmd = [
            ffmpeg_path,
            '-y',  # ファイル上書き許可
            '-i', video_file,
            '-c:v', 'libx264',
            '-b:v', f'{target_bitrate}k',
            '-pass', '2',
            '-passlogfile', log_file,
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
                second_pass_only=True
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
        ffmpeg_path = os.path.normpath('bin/ffmpeg.exe')
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
        # 1pass解析中であることを明示
        if progress_percent < 100:
            self.convert_button.setText(f'1pass解析中... ({int(progress_percent)}%)')
        else:
            self.convert_button.setText('1pass解析完了')

    def update_twopass_progress(self, progress_percent):
        """2pass変換の全体プログレスを更新（0-100%を1pass/2passに分割）"""
        if progress_percent <= 50:
            # 0-50% : 1pass目
            self.pass1_progress_bar.setValue(int(progress_percent * 2))
            self.pass2_progress_bar.setValue(0)
        else:
            # 50-100% : 2pass目
            self.pass1_progress_bar.setValue(100)
            self.pass2_progress_bar.setValue(int((progress_percent - 50) * 2))

    def update_progress(self, progress_percent):
        """CRF変換のプログレスバーを更新"""
        self.single_progress_bar.setValue(int(progress_percent))

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
                
            # 変換完了ポップアップを表示
            self.show_completion_dialog(output_path)
        else:
            self.text_edit.add_log("=== 変換失敗 ===")
            if error_message:
                self.text_edit.add_log(f"エラー: {error_message}")
                
            # エラーポップアップを表示
            error_box = QMessageBox(self)
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("変換エラー")
            error_box.setText("動画変換に失敗しました")
            error_box.setDetailedText(error_message if error_message else "不明なエラーが発生しました")
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec_()

    def show_completion_dialog(self, output_path):
        """変換完了ダイアログを表示"""
        msg_box = QMessageBox(self)
        
        # ランダム画像選択機能
        custom_icon_path = self.get_random_completion_icon()
        
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
        
        # ボタンにテーマスタイルを適用
        ThemeManager.apply_theme_to_widget(ok_button, self.current_theme)
        ThemeManager.apply_theme_to_widget(folder_button, self.current_theme)
        
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
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            min-width: 80px;
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
        msg_box.exec_()
        
        # クリックされたボタンを確認
        if msg_box.clickedButton() == folder_button:
            self.open_output_folder(output_path)

    def get_random_completion_icon(self):
        """ランダムな変換完了アイコンを取得"""
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
            if os.path.exists(folder):
                for extension in image_extensions:
                    pattern = os.path.join(folder, extension)
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
            if os.path.exists(potential_path):
                return potential_path
        
        return None

    def open_output_folder(self, file_path):
        """出力ファイルのフォルダを開く"""
        try:
            import subprocess
            import platform
            
            folder_path = os.path.dirname(file_path)
            
            if platform.system() == "Windows":
                # Windowsの場合、エクスプローラーでファイルを選択状態で開く
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
                self.text_edit.add_log(f"フォルダを開きました: {folder_path}")
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', '-R', file_path])
                self.text_edit.add_log(f"Finderでフォルダを開きました: {folder_path}")
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
                self.text_edit.add_log(f"フォルダを開きました: {folder_path}")
                
        except Exception as e:
            self.text_edit.add_log(f"フォルダオープンエラー: {e}")
            # エラーの場合は通常のフォルダオープンを試行
            try:
                if platform.system() == "Windows":
                    os.startfile(folder_path)
                else:
                    subprocess.run(['open' if platform.system() == "Darwin" else 'xdg-open', folder_path])
            except:
                self.text_edit.add_log("フォルダを開くことができませんでした")

    def get_selected_video_file(self):
        """現在選択されている動画ファイルのパスを取得"""
        return self.text_edit.video_file_path

    def create_menu_bar(self):
        """メニューバーを作成"""
        menubar = self.menuBar()
        
        # 表示メニュー
        view_menu = menubar.addMenu('表示')
        
        # テーマサブメニュー
        theme_menu = view_menu.addMenu('テーマ')
        
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
        
        # ヘルプメニュー
        help_menu = menubar.addMenu('ヘルプ')
        
        # Aboutアクション
        about_action = QAction('ClipItBro について', self)
        about_action.setShortcut('F1')
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def show_about_dialog(self):
        """Aboutダイアログを表示"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()
    
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
            
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # stderrもstdoutにリダイレクト
                text=True,
                env=self.env,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True
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
    
    def __init__(self, video_file_path, temp_bitrate, total_duration=0):
        super().__init__()
        self.video_file_path = video_file_path
        self.temp_bitrate = temp_bitrate
        self.total_duration = total_duration  # 動画の総時間を追加
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
            ffmpeg_path = os.path.normpath('bin/ffmpeg.exe')
            
            # 1pass目用のログファイル名を生成
            video_dir = os.path.dirname(self.video_file_path)
            video_name = os.path.splitext(os.path.basename(self.video_file_path))[0]
            log_file = os.path.join(video_dir, f"ffmpeg2pass-{video_name}")
            
            # 1pass目のコマンド構築
            cmd = [
                ffmpeg_path,
                '-y',  # ファイル上書き許可
                '-i', self.video_file_path,
                '-c:v', 'libx264',
                '-b:v', f'{self.temp_bitrate}k',
                '-pass', '1',
                '-passlogfile', log_file,
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
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True
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
                self.finished_signal.emit(True, log_file, "")
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
    
    def __init__(self, video_file_path, output_path, target_bitrate, total_duration, second_pass_only=False):
        super().__init__()
        self.video_file_path = video_file_path
        self.output_path = output_path
        self.target_bitrate = target_bitrate
        self.total_duration = total_duration
        self.second_pass_only = second_pass_only
        
        # 環境変数設定
        self.env = os.environ.copy()
        self.env['PYTHONIOENCODING'] = 'utf-8'
        if os.name == 'nt':
            self.env['LANG'] = 'ja_JP.UTF-8'
    
    def run(self):
        try:
            ffmpeg_path = os.path.normpath('bin/ffmpeg.exe')
            
            # ログファイル名を生成
            video_dir = os.path.dirname(self.video_file_path)
            video_name = os.path.splitext(os.path.basename(self.video_file_path))[0]
            log_file = os.path.join(video_dir, f"ffmpeg2pass-{video_name}")
            
            if not self.second_pass_only:
                # === 1pass目実行 ===
                self.phase_signal.emit(1)
                self.log_signal.emit("=== 1pass目開始 ===")
                
                cmd1 = [
                    ffmpeg_path,
                    '-y',
                    '-i', self.video_file_path,
                    '-c:v', 'libx264',
                    '-b:v', f'{self.target_bitrate}k',
                    '-pass', '1',
                    '-passlogfile', log_file,
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
            
            cmd2 = [
                ffmpeg_path,
                '-y',
                '-i', self.video_file_path,
                '-c:v', 'libx264',
                '-b:v', f'{self.target_bitrate}k',
                '-pass', '2',
                '-passlogfile', log_file,
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
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self.env,
                encoding='utf-8',
                errors='replace',
                universal_newlines=True
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
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("About ClipItBro")
        self.setFixedSize(700, 400)  # ダイアログサイズをさらに拡大
        self.setWindowIcon(self.get_app_icon())
        
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
        app_name = QLabel("ClipItBro")
        app_name.setFont(QFont("Arial", 22, QFont.Bold))
        app_name.setObjectName("app_name")
        
        # バージョン情報
        version_label = QLabel("1.0")
        version_label.setFont(QFont("Arial", 11))
        version_label.setObjectName("version_label")
        
        # サブタイトル（同じ行に追加）
        subtitle_label = QLabel("powered by 菊池組")
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
        creator_label = QLabel("菊池組(KIKUCHIGUMI)は、2020年から本格的な活動を開始した、異能マルチクリエイター集団。アニメ・ゲームカルチャーから影響を受けた独自のクリエイティビティで、多方面での活動を展開している。2025年には新たに三角さこんを迎え、VALORANTシーンにも活動の幅を広めている。")
        creator_label.setFont(QFont("Arial", 11))
        creator_label.setObjectName("creator_label")
        creator_label.setWordWrap(True)
        creator_label.setAlignment(Qt.AlignLeft)

        # コピーライト
        copyright_label = QLabel("Built with FFmpeg - https://ffmpeg.org\nFFmpeg is licensed under the LGPL/GPL.\n\n© 2025 菊池組. All rights reserved.")
        copyright_label.setFont(QFont("Arial", 9))
        copyright_label.setObjectName("copyright_label")
        copyright_label.setAlignment(Qt.AlignLeft)
        text_layout.addWidget(creator_label)
        text_layout.addWidget(copyright_label)
        
        # 下部スペーサー
        text_layout.addStretch()
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.setObjectName("close_button")
        close_button.clicked.connect(self.accept)
        text_layout.addWidget(close_button, 0, Qt.AlignRight)
        
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
        """
        self.setStyleSheet(dialog_style)
    
    def get_app_icon(self):
        """アプリケーションアイコンを取得"""
        icon_paths = ["icon/app.ico", "icon/app.png", "app.ico", "app.png"]
        for path in icon_paths:
            if os.path.exists(path):
                return QIcon(path)
        return QIcon()
    
    def get_logo_image(self):
        """制作者ロゴ画像を取得（GIF対応）"""
        logo_paths = ["icon/logo.gif", "icon/logo.png", "icon/logo.jpg", "icon/logo.ico", 
                     "logo.gif", "logo.png", "logo.jpg", "logo.ico"]
        for path in logo_paths:
            if os.path.exists(path):
                return path  # ファイルパスを返す（GIFとPNG/JPGの両方に対応）
        return None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
