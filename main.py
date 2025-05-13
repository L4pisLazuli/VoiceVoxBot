import discord
from discord import app_commands
import asyncio
import tempfile
import os
import voicevox

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client, fallback_to_global=False)

voicevox_client = voicevox.Client()
with open('.env', 'r') as f:
    TOKEN = f.readline()
    FFMPEG_PATH = f.readline()


@client.event
async def on_ready():
    print('successfully Loggined as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(name="test"))
    await tree.sync()

@tree.command(name="join", description="ボイスチャンネルに参加します")
async def join(interaction: discord.Interaction):
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
    if not interaction.guild.voice_client:
        await interaction.response.send_message("ボイスチャンネルに接続していません。", ephemeral=True)
        return

    try:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("ボイスチャンネルから退出しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "聞き専":
        if message.guild.voice_client and message.guild.voice_client.is_connected():
            try:
                audio_queries = await voicevox_client.create_audio_query(message.content, speaker=1)
                wav = await voicevox.AudioQuery.synthesis(audio_queries, speaker=1)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as fp:
                    fp.write(wav)
                    fp.flush()
                    
                    voice_client = message.guild.voice_client
                    voice_client.play(discord.FFmpegPCMAudio(
                        executable= FFMPEG_PATH,
                        source=fp.name,
                        options="-filter:a atempo=2.0,volume=0.7"
                    ))
                    
                    while voice_client.is_playing():
                        await asyncio.sleep(0.1)
                    
                    os.unlink(fp.name)
            except Exception as e:
                print(f"音声生成中にエラーが発生しました: {e}")


client.run(TOKEN)
