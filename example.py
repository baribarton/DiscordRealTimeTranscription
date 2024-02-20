import asyncio
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.sinks import RecordingException

from audio_management import connection_manager
from audio_management.voice_client_culler import VoiceClientCuller

bot = commands.Bot(command_prefix='/', intents=discord.Intents.default(), help_command=None)

voice_client_culler = VoiceClientCuller(bot)


@bot.event
async def on_ready():
    print(f'{bot.user.name} is ready to scribble!')
    asyncio.create_task(voice_client_culler.start())


@bot.slash_command()
async def start_transcription(ctx):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("You aren't in a voice channel!")
        return

    bot_voice_client = ctx.guild.voice_client

    # Check if the bot has connected to a voice client before and has a context
    if bot_voice_client:
        # Check if it's still connected or not
        if bot_voice_client.is_connected():
            await ctx.respond("I'm already in your voice channel!")
            return

    await ctx.respond("Joining channel to take notes")
    try:
        await connection_manager.connect_to_voice_channel(ctx.guild, voice.channel)
        voice_client_culler.last_voice_activity_times[ctx.guild.id] = datetime.now()
    except Exception as e:
        print(f"Failed to connect to voice channel: {e}")


@bot.slash_command()
async def stop_transcription(ctx):
    server_id = ctx.guild.id

    if server_id in connection_manager.voice_connections:  # Check if the guild is in the cache.
        voice_connection = connection_manager.voice_connections[server_id]
        voice_connection.mark_for_deletion()
        voice_client = voice_connection.voice_client
        sink = voice_connection.sink

        try:
            voice_client.stop_recording()  # Stop recording, and call the callback (once_done).
        except RecordingException as e:
            print(f"Tried to stop recording but couldn't: {e}")
            await sink.vc.disconnect()

        sink.speech_to_text_converter.audio_cost_calculator.session_end_time = time.time()
        await ctx.respond("Stopping transcription tasks")
        await sink.stop_transcription_tasks()

        del connection_manager.voice_connections[server_id]
        del voice_client_culler.last_voice_activity_times[server_id]
        sink.speech_to_text_converter.audio_cost_calculator.save_cost_metrics()


bot.run('TOKEN')
