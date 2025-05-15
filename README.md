# Discord VOICEVOX Bot

DiscordでテキストをVOICEVOXを使用して音声読み上げするボットです。

## 必要条件

- Python 3.8以上
- VOICEVOX Engine（ローカルで実行）
- FFmpeg

## セットアップ

1. 必要なパッケージをインストール:
```bash
pip install -r requirements.txt
```

2. `.env`ファイルを作成し、以下の内容を設定:
```
DISCORD_TOKEN
FFMPEG_PATH
```

3. VOICEVOX Engineを起動:
- [VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine)をダウンロードして起動
- デフォルトで`http://localhost:50021`で起動

## 使用方法

1. ボットを起動:
```bash
python main.py
```

2. Discordで以下のコマンドを使用:

- `/join` - ボットをボイスチャンネルに参加させる
- `/leave` - ボットをボイスチャンネルから退出させる
- `/speakers` - 利用可能な話者の一覧を表示
- `/speaker [ID]` - 使用する話者を設定
- `/speed [1.0-3.0]` - 音声の再生速度を設定

3. 「聞き専」チャンネルに投稿されたメッセージは自動的に音声読み上げされます。

## 注意事項

- VOICEVOX Engineが起動していないとボットは動作しません
- 音声速度は1.0〜3.0の間で設定可能です
- 話者IDは`/speakers`コマンドで確認できます
