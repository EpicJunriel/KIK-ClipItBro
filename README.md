ClipItBro - powered by 菊池組
====================================

## 概要
ClipItBroは、動画ファイルをソーシャル向けのサイズに圧縮することを目的として開発されたPyQt5ベースのGUIアプリケーションです。

### 🎯 変換方式
- **2pass方式**: ファイルサイズを元にした変換方式
- **CRF方式**: 品質を元にした変換方式

## 使用方法
### 基本操作
1. **アプリケーション起動**: main.pyを実行
2. **ファイル読み込み**: 動画ファイルをテキストエリアにドラッグ&ドロップ
3. **自動分析**: 1pass分析が自動実行され、最適設定が計算されます
4. **変換方式選択**: 
   - **2pass**: ファイルサイズスライダーで目標サイズを設定
   - **CRF**: CRFスライダーで品質レベルを調整
5. **変換実行**: 「変換実行」ボタンをクリック
6. **進行確認**: デュアルプログレスバーで1pass/2passの進行状況を監視

### 高度な操作
- **テーマ切り替え**: メニューバー「表示」→「テーマ」から選択
- **変換方式切り替え**: 2pass/CRFボタンでワンクリック切り替え

## 出力ファイル形式
```
ClipItBro_YYYY_MM_DD_HH_MM_SS_[変換方式]_[元ファイル名].mp4
```

例：
- ClipItBro_2025_08_27_20_15_30_2pass_samplevideo.mp4
- ClipItBro_2025_08_27_20_15_30_CRF_samplevideo.mp4

## ライセンス

ClipItBro本体は **MIT License** の下で提供されています。詳細は `LICENSE` ファイルをご確認ください。

### 依存関係のライセンス
- **PyQt5**: GPL v3 または Commercial License
- **FFmpeg**: LGPL v2.1+ (一部コーデックはGPL v2+)
- **Python**: Python Software Foundation License

### 重要な注意事項
- FFmpegのバイナリはリポジトリに含まれていません。ユーザーが別途ダウンロードして `bin/` フォルダに配置する必要があります

---
© 2025 ClipItBro by KIKUCHIGUMI - Professional Video Conversion Tool
