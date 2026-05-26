# ~/~ begin <<README.md#discord-client>>[init]
# ~/~ begin <<README.md#discord-client-uv-dependencies>>[init]
# /// script
# dependencies = [
#   "discord.py[voice]",
#   "pynacl",
#   "requests",
# ]
# ///
# ~/~ end
# ~/~ begin <<README.md#discord-client-imports>>[init]
import discord
from discord.ext import commands
import discord.ext
import os
# ~/~ end
# ~/~ begin <<README.md#discord-client-imports>>[1]
import requests
# ~/~ end
# ~/~ begin <<README.md#discord-client-imports>>[2]
import subprocess
import socket
# ~/~ end
# ~/~ begin <<README.md#discord-client-globals>>[init]
TTSOUNDBOARD_IP = "127.0.0.1"
TTSOUNDBOARD_API_PORT = "6973"
TTSOUNDBOARD_TCP_PORT = "5212"
FRAME_SIZE = 3840
# ~/~ end
# ~/~ begin <<README.md#discord-client-globals>>[1]
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)
# ~/~ end
# ~/~ begin <<README.md#discord-client-globals>>[2]
TEXT_CHANNEL = None
AUTHOR = None
# ~/~ end
# ~/~ begin <<README.md#discord-client-functions>>[init]
@bot.command()
async def textconnect(ctx):
    global TEXT_CHANNEL
    global AUTHOR

    if TEXT_CHANNEL != None or AUTHOR != None:
        await ctx.send("Already connected to text channel")
        return
    TEXT_CHANNEL = ctx.channel
    AUTHOR = ctx.author
    await ctx.send(f"Connected to user {AUTHOR} on channel {TEXT_CHANNEL}")

@bot.command()
async def textdisconnect(ctx):
    global TEXT_CHANNEL
    global AUTHOR

    if ctx.author != AUTHOR:
        await ctx.send("")
        return
    TEXT_CHANNEL = None
    AUTHOR = None
    await ctx.send("Disconnected from text channel")

@bot.listen()
async def on_message(message):
    global TEXT_CHANNEL
    global AUTHOR

    if message.channel != TEXT_CHANNEL or message.author != AUTHOR: return

    # ~/~ begin <<README.md#discord-client-requests>>[init]
    match (message.content):
        case ";p":
            print("Sent pause API request")
            requests.post(f"http://{TTSOUNDBOARD_IP}:{TTSOUNDBOARD_API_PORT}/pause")
        case ";r":
            print("Sent resume API request")
            requests.post(f"http://{TTSOUNDBOARD_IP}:{TTSOUNDBOARD_API_PORT}/resume")
        case ";s":
            print("Sent stop API request")
            requests.post(f"http://{TTSOUNDBOARD_IP}:{TTSOUNDBOARD_API_PORT}/stop")
        case _:
            if message.content[:2] == ";v":
                print(f"Changing voice to {message.content[3:]}")
                requests.post(f"http://{TTSOUNDBOARD_IP}:{TTSOUNDBOARD_API_PORT}/voice", data=message.content[3:].encode())
            else:
                print("Sending message to be spoken")
                requests.post(f"http://{TTSOUNDBOARD_IP}:{TTSOUNDBOARD_API_PORT}/speak", data=message.content.encode())
    # ~/~ end
# ~/~ end
# ~/~ begin <<README.md#discord-client-functions>>[1]
ffmpeg = None
@bot.command()
async def voiceconnect(ctx):
    await ctx.author.voice.channel.connect()
    vc = ctx.voice_client

    global ffmpeg
    ffmpeg = subprocess.Popen([
        "ffmpeg",
        "-i", f"tcp://{TTSOUNDBOARD_IP}:{TTSOUNDBOARD_TCP_PORT}",
        "-f", "wav",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-ar", "48000",
        "-ac", "2",
        "pipe:1"
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    vc.play(discord.PCMAudio(ffmpeg.stdout))


@bot.command()
async def voicedisconnect(ctx):
    global ffmpeg
    ffmpeg.kill()
    ffmpeg.wait(timeout=2)

    ctx.voice_client.stop()
    await ctx.voice_client.disconnect(force=True)
# ~/~ end
# ~/~ end
# ~/~ begin <<README.md#discord-client>>[1]
bot.run(DISCORD_BOT_TOKEN)
# ~/~ end
