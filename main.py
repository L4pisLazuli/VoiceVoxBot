import discord
from discord import app_commands
import asyncio
import tempfile
import os
import voicevox
from collections import deque
import aiohttp
from typing import List, Dict, Any

# 定数
VOICEVOX_URL = "http://localhost:50021"
DEFAULT_VOICE_SPEED = 2.0
DEFAULT_SPEAKER_ID = 1
MAX_MESSAGE_LENGTH = 1900

# Discordクライアントの設定
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client, fallback_to_global=False)

# VOICEVOXクライアントの初期化
voicevox_client = voicevox.Client()

# 環境変数の読み込み
def load_env() -> tuple[str, str]:
    """環境変数を読み込む関数"""
    with open('.env', 'r') as f:
        return f.readline().strip(), f.readline().strip()

TOKEN, FFMPEG_PATH = load_env()

# グローバル変数
voice_speed = DEFAULT_VOICE_SPEED
current_speaker = DEFAULT_SPEAKER_ID
message_queue = deque()
is_processing = False

async def check_voicevox_status() -> bool:
    """VOICEVOXの起動状態を確認する関数"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{VOICEVOX_URL}/version") as response:
                if response.status == 200:
                    version = await response.text()
                    print(f"VOICEVOXが起動しています。バージョン: {version}")
                    return True
                print("VOICEVOXが起動していません。")
                return False
    except Exception as e:
        print(f"VOICEVOXの接続に失敗しました: {e}")
        return False

async def get_valid_speaker_ids() -> List[int]:
    """有効な話者IDのリストを取得する関数"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{VOICEVOX_URL}/speakers") as response:
            speakers = await response.json()
            return [style["id"] for speaker in speakers for style in speaker["styles"]]

async def process_message_queue(guild: discord.Guild) -> None:
    """メッセージキューを処理する関数"""
    global is_processing
    if is_processing or not message_queue:
        return

    is_processing = True
    while message_queue:
        message = message_queue.popleft()
        temp_file = None
        try:
            # VOICEVOXで音声を生成
            audio_queries = await voicevox_client.create_audio_query(message, speaker=current_speaker)
            wav = await voicevox.AudioQuery.synthesis(audio_queries, speaker=current_speaker)
            
            # 一時ファイルに音声を保存
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.write(wav)
            temp_file.flush()
            temp_file.close()
            
            # 音声を再生
            voice_client = guild.voice_client
            voice_client.play(discord.FFmpegPCMAudio(
                executable=FFMPEG_PATH,
                source=temp_file.name,
                options=f"-filter:a atempo={voice_speed},volume=0.7"
            ))
            
            # 再生が終わるまで待機
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"音声生成中にエラーが発生しました: {e}")
        finally:
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception as e:
                    print(f"一時ファイルの削除中にエラーが発生しました: {e}")
    
    is_processing = False

# Discordイベントハンドラ
@client.event
async def on_ready():
    """Botが起動したときに実行されるイベント"""
    print(f'成功: {client.user}としてログインしました')
    await client.change_presence(activity=discord.Game(name="VOICEVOX読み上げ"))
    await tree.sync()
    
    if not await check_voicevox_status():
        print("VOICEVOXを起動してください。")
        print("終了します...")
        await client.close()
        return

@client.event
async def on_message(message: discord.Message):
    """メッセージを受信したときに実行されるイベント"""
    if message.author.bot:
        return

    if message.channel.name == "聞き専":
        if message.guild.voice_client and message.guild.voice_client.is_connected():
            message_queue.append(message.content)
            await process_message_queue(message.guild)

# コマンドハンドラ
@tree.command(name="join", description="ボイスチャンネルに参加します")
async def join(interaction: discord.Interaction):
    """ユーザーがいるボイスチャンネルにBotが参加するコマンド"""
    if not interaction.user.voice:
        await interaction.response.send_message("ボイスチャンネルに参加してください。", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    try:
        await voice_channel.connect()
        await interaction.response.send_message(f"{voice_channel.name}に参加しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@tree.command(name="leave", description="ボイスチャンネルから退出します")
async def leave(interaction: discord.Interaction):
    """Botがボイスチャンネルから退出するコマンド"""
    if not interaction.guild.voice_client:
        await interaction.response.send_message("ボイスチャンネルに接続していません。", ephemeral=True)
        return

    try:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("ボイスチャンネルから退出しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@tree.command(name="speed", description="音声の速度を設定します（1.0〜3.0）")
async def set_speed(interaction: discord.Interaction, speed: float):
    """音声の再生速度を設定するコマンド"""
    global voice_speed
    if 1.0 <= speed <= 3.0:
        voice_speed = speed
        await interaction.response.send_message(f"音声速度を{speed}に設定しました。", ephemeral=True)
    else:
        await interaction.response.send_message("速度は1.0から3.0の間で設定してください。", ephemeral=True)

@tree.command(name="speakers", description="利用可能な話者の一覧を表示します")
async def list_speakers(interaction: discord.Interaction):
    """VOICEVOXで利用可能な話者の一覧を表示するコマンド"""
    try:
        speakers_list = []
        current_message = "利用可能な話者一覧:\n"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{VOICEVOX_URL}/speakers") as response:
                speakers = await response.json()
                for speaker in speakers:
                    name = speaker["name"]
                    style_names = [style["name"] for style in speaker["styles"]]
                    style_ids = [style["id"] for style in speaker["styles"]]
                    speaker_info = zip(style_ids, style_names)
                    
                    for style_id, style_name in speaker_info:
                        line = f"{name} - {style_name} (id:{style_id})\n"
                        if len(current_message) + len(line) > MAX_MESSAGE_LENGTH:
                            speakers_list.append(current_message)
                            current_message = line
                        else:
                            current_message += line
        
        if current_message:
            speakers_list.append(current_message)
        
        await interaction.response.send_message(speakers_list[0], ephemeral=True)
        for message in speakers_list[1:]:
            await interaction.followup.send(message, ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"話者一覧の取得に失敗しました: {str(e)}", ephemeral=True)

@tree.command(name="speaker", description="使用する話者を設定します")
async def set_speaker(interaction: discord.Interaction, speaker_id: int):
    """使用する話者を設定するコマンド"""
    global current_speaker
    try:
        valid_ids = await get_valid_speaker_ids()
        if speaker_id in valid_ids:
            current_speaker = speaker_id
            await interaction.response.send_message(f"話者IDを「{speaker_id}」に設定しました。", ephemeral=True)
        else:
            await interaction.response.send_message("指定されたIDの話者は存在しません。`/speakers`コマンドで利用可能な話者を確認してください。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"話者の設定に失敗しました: {str(e)}", ephemeral=True)

# Botを起動
if __name__ == "__main__":
    client.run(TOKEN)
