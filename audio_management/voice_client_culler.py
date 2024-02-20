import asyncio
from datetime import datetime, timedelta

import discord
from discord.errors import HTTPException, NotFound, ClientException

from audio_management import connection_manager

"""
Manages killing voice connections that are in bad states and connecting new fresh ones. This is because sometimes due to
various networking issues, the connection can get into a state where audio isn't being recorded but the bot is still connected to the server
"""


class VoiceClientCuller:
    def __init__(self, bot_client):
        """
        Initializes the VoiceClientCuller.

        :param bot_client: The Discord bot client instance used to interact with Discord servers (guilds).
        """
        self.bot_client = bot_client
        self.interval_seconds = 5  # Interval in seconds between each culling check.
        self.audio_activity_threshold = timedelta(minutes=7)  # threshold to consider a voice connection inactive.
        self.last_voice_activity_times = {}

    async def start(self):
        """
        Starts the culling process that periodically manages voice connections.
        """
        print("Started The Culling")
        while True:
            try:
                await asyncio.sleep(self.interval_seconds)
                await self.check_audio_activity()
            except Exception as e:
                error_type = e.__class__.__name__
                print(f"Error during The Culling. {error_type}: {e}")

    async def check_audio_activity(self):
        """
        Checks for audio activity in all managed voice connections and resets connections deemed inactive.
        """
        current_time = datetime.now()
        # print(self.last_voice_activity_times)
        for server_id, voice_connection in list(connection_manager.voice_connections.items()):
            if voice_connection.deleting:  # Skip connections marked for deletion.
                print(f"Skipping server {server_id} as it's marked for deletion.")
                continue

            sink = voice_connection.sink
            last_write_times = sink.audio_buffer_manager.last_write_times

            most_recent_write_time = datetime.fromtimestamp(
                max(last_write_times.values())) if last_write_times else datetime.min
            last_voice_activity_time = self.last_voice_activity_times[server_id]
            self.last_voice_activity_times[server_id] = max(last_voice_activity_time, most_recent_write_time)
            # print(self.last_voice_activity_times[server_id])

            if not current_time - self.last_voice_activity_times[server_id] < self.audio_activity_threshold:
                print(f"No recent audio activity detected. Attempting to reset connection...")
                try:
                    guild = await self.bot_client.fetch_guild(server_id)
                except NotFound:
                    print(f"Guild with ID {server_id} not found.")
                    continue  # Skip trying to reconnect if the guild doesn't exist
                except HTTPException as e:
                    print(f"Failed to fetch guild with ID {server_id}: {e}")
                    continue  # Skip trying to reconnect if there was an HTTP error during fetch
                except Exception as e:
                    print(f"Failed to fetch guild with ID {server_id}: {e}")
                    continue

                voice_client = discord.utils.get(self.bot_client.voice_clients, guild=guild)
                if voice_client:
                    await self.hard_reset_voice_connection(guild, server_id, voice_connection)
                else:
                    print("The bot isn't connected. Not resetting the connection.")

    async def hard_reset_voice_connection(self, guild, server_id, voice_connection):
        """
        Performs a hard reset on a specific voice connection by ending all tasks associated with the connection and then reconnecting.
        There may be some redundancy in stopping some of the tasks (some of them should be stopped by disconnecting), but
        since it is very important to get the connection to a good state again, we manually stop and disconnect everything.
        Ergo a "hard" reset

        :param guild: The guild object associated with the voice connection.
        :param server_id: The ID of the server (guild) for which the voice connection is being reset.
        :param voice_connection: The VoiceConnection object to reset.
        """
        voice_client = voice_connection.voice_client
        sink = voice_connection.sink

        # Stop all connection activity
        voice_client.stop_recording()
        await voice_client.disconnect(force=True)
        await sink.stop_transcription_tasks()

        # If the connection is still present and not marked for deletion, delete and reconnect.
        if server_id in connection_manager.voice_connections and not voice_connection.deleting:
            try:
                del connection_manager.voice_connections[server_id]
                await connection_manager.connect_to_voice_channel(guild, voice_connection.active_voice_channel)
            except (ClientException, Exception) as e:
                print(f"Couldn't connect during hard reset. {e}")
                # Add the voice connection back, so we maintain the correct state
                connection_manager.voice_connections[server_id] = voice_connection
        else:
            print("Looks like the connection is about to be deleted. Not resetting the connection")
