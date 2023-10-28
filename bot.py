import json
import os
from typing import List, Optional

from twitchio.ext import commands

from build import Build

BUILDS_FILENAME = 'builds.json'
CURRENT_BUILD = 'current_build'


class Bot(commands.Bot):

    def __init__(
            self,
            token: str,
            client_id: str,
            nick: str,
            prefix: str,
            initial_channels: List[str],
            **kwargs
    ):
        super().__init__(
            token=token,
            client_id=client_id,
            nick=nick,
            prefix=prefix,
            initial_channels=initial_channels,
            **kwargs
        )
        self.builds = self.load_builds(channels=initial_channels)
        self.dc_count = {
            channel_name: 0
            for channel_name in initial_channels
        }

    @staticmethod
    def load_builds(channels: Optional[List[str]] = None):
        builds = {}
        if channels:
            for channel_name in channels:
                builds[channel_name] = {}
        with open(BUILDS_FILENAME) as f:
            try:
                builds_json = json.load(f)
            except json.JSONDecodeError:
                builds_json = {}
        for channel_name, channel_builds in builds_json.items():
            builds[channel_name] = {}
            for build_name, build_info in channel_builds.items():
                builds[channel_name][build_name] = Build(**build_info)
        return builds

    def dump_builds(self):
        with open(BUILDS_FILENAME, 'w') as f:
            json.dump({
                channel_name: {
                    build_name: build.to_json()
                    for build_name, build in channel_builds.items()
                } for channel_name, channel_builds in self.builds.items()
            },
                fp=f,
                ensure_ascii=False,
                indent=4,
            )

    async def event_ready(self):
        print(f'Logged in {", ".join([channel.name for channel in self.connected_channels])} as {self.nick}. '
              f'The bot is ready!')

    def add_build(self, channel_name: str, build: Build):
        if build.name in self.builds[channel_name]:
            raise ValueError('A build with this name already exists!')
        self.builds[channel_name][build.name] = build
        self.dump_builds()

    def remove_build(self, channel_name: str, build_name: str):
        if build_name not in self.builds[channel_name]:
            raise ValueError('A build with this name is not found!')
        del self.builds[channel_name][build_name]
        if CURRENT_BUILD in self.builds[channel_name] and self.builds[channel_name][CURRENT_BUILD].name == build_name:
            del self.builds[channel_name][CURRENT_BUILD]
        self.dump_builds()

    def set_build(self, channel_name: str, build_name: str):
        if build_name not in self.builds[channel_name]:
            raise ValueError('A build with this name is not found!')
        self.builds[channel_name][CURRENT_BUILD] = self.builds[channel_name][build_name]
        self.dump_builds()

    def get_current_build(self, channel_name: str):
        if CURRENT_BUILD in self.builds[channel_name]:
            return self.builds[channel_name][CURRENT_BUILD].print()
        return 'No build set.'

    def get_rune_level(self, channel_name: str):
        if CURRENT_BUILD in self.builds[channel_name]:
            current_build = self.builds[channel_name][CURRENT_BUILD]
            return ('RL' + str(current_build.rune_level) +
                    f' +{current_build.regular_upgrade_level}/+{current_build.somber_upgrade_level}')
        return 'No build set.'

    def get_stats(self, channel_name: str):
        if CURRENT_BUILD in self.builds[channel_name]:
            return self.builds[channel_name][CURRENT_BUILD].print_stats()
        return 'No build set.'

    @commands.command()
    async def hi(self, ctx: commands.Context):
        await ctx.send(f'Ayo @{ctx.author.name}!')

    @commands.command()
    async def addbuild(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        if not ctx.author.is_mod:
            return
        try:
            build = Build.from_url(ctx.message.content)
            self.add_build(channel_name, build)
            await ctx.send(f'Build {build.name} has been added.')
        except Exception as exception:
            await ctx.send(str(exception))

    @commands.command()
    async def addbuildfromtext(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        if not ctx.author.is_mod:
            return
        try:
            build = Build.from_text(ctx.message.content)
            self.add_build(channel_name, build)
            await ctx.send(f'Build {build.name} has been added.')
        except Exception as exception:
            await ctx.send(str(exception))

    @commands.command()
    async def removebuild(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        if not ctx.author.is_mod:
            return
        build_name = ' '.join(ctx.message.content.split()[1:])
        try:
            self.remove_build(channel_name, build_name)
            await ctx.send(f'Build {build_name} has been removed.')
        except Exception as exception:
            await ctx.send(str(exception))

    @commands.command()
    async def setbuild(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        if not ctx.author.is_mod:
            return
        build_name = ' '.join(ctx.message.content.split()[1:])
        try:
            self.set_build(channel_name, build_name)
            await ctx.send(f'Current build has been set to {build_name}.')
        except Exception as exception:
            await ctx.send(str(exception))

    @commands.command()
    async def build(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        await ctx.send(self.get_current_build(channel_name))

    @commands.command(aliases=['sl'])
    async def rl(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        await ctx.send(self.get_rune_level(channel_name))

    @commands.command()
    async def stats(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        stats = self.get_stats(channel_name)
        if stats:
            await ctx.send(stats)

    @commands.command()
    async def builds(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        er_inventory_user_id = json.loads(os.environ["ER_INVENTORY_USER_IDS"]).get(channel_name, None)
        if er_inventory_user_id is not None:
            await ctx.send(
                f'You can find my public builds here: '
                f'{"https://er-inventory.nyasu.business/browse/" + er_inventory_user_id}'
            )

    @commands.command()
    async def setdccount(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        if not ctx.author.is_broadcaster:
            return
        starting_count: str = ctx.message.content.split()[1]
        if starting_count.isdigit():
            self.dc_count[channel_name] = int(starting_count)
            await ctx.send(f'DC count has been set to {starting_count}.')
        else:
            await ctx.send('It seems like the provided value is not a valid number.')

    @commands.command()
    async def dc(self, ctx: commands.Context):
        channel_name = ctx.channel.name
        if ctx.author.is_broadcaster:
            self.dc_count[channel_name] += 1
        dc_count = self.dc_count[channel_name]
        if dc_count % 10 == 1 and dc_count % 100 != 11:
            await ctx.send(f'A connection error occurred {dc_count} time.')
            return
        await ctx.send(f'A connection error occurred {dc_count} times.')
