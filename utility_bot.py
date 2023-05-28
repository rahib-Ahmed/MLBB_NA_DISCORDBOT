import discord
from discord.ext import commands
from discord.utils import get
import psycopg2

# Database connection settings
db_host = 'localhost'
db_user = 'postgres'
db_password = 'password'
db_name = 'bot_mlbb_1'

# initial role options for the interface
role_options = ['Role 1', 'Role 2', 'Role 3']

# initial emoji mapping
emoji_role_mapping = {
    '1\u20e3': 'Role 1',
    '2\u20e3': 'Role 2',
    '3\u20e3': 'Role 3'
}

# intents for the discord
intents = discord.Intents.default()
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def connect_to_database():
    """Connect to the postgres database"""
    connection = psycopg2.connect(
        host=db_host,
        dbname=db_name,
        user=db_user,
        password=db_password
    )
    return connection




@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


@bot.command(name="geniusRole")
@commands.has_permissions(manage_roles=True)
async def create_reaction_role_panel(ctx, panel_type):
    """Make or select role based on the Lead and User"""
    guild = ctx.guild
    panel_type = panel_type.lower()

    if panel_type == 'single':
        description = 'Choose only one role from the options below:'
        multiple = False
    elif panel_type == 'multiple':
        description = 'Choose any number of roles from the options below:'
        multiple = True
    else:
        await ctx.send('Invalid panel type. Please choose either "single" or "multiple".')
        return


    embed = discord.Embed(title='Reaction Role Panel', description=description, color=discord.Color.blue())
    added_roles = []  # Store the added roles

    for index, role_name in enumerate(role_options, start=1):
        existing_role = get(guild.roles, name=role_name)
        if existing_role is None:
            role = await guild.create_role(name=role_name)
            added_roles.append(role)
        else:
            role = existing_role
        embed.add_field(name=f'Option {index}', value=role.mention, inline=False)

    msg = await ctx.send(embed=embed)
    for index in range(1, len(role_options) + 1):
        await msg.add_reaction(f'{index}\u20e3')
    # Store the panel information in the database
    connection = connect_to_database()
    cursor = connection.cursor()

    query = "INSERT INTO reaction_panels (message_id, guild_id, panel_type, allow_multiple) VALUES (%s, %s, %s, %s)"
    values = (msg.id, guild.id, panel_type, multiple)
    cursor.execute(query, values)

    connection.commit()
    cursor.close()
    connection.close()

    for reaction in msg.reactions:
    # If the reaction is not already in the list of added roles, remove it.
        print(reaction.emoji, "emoji", role_options)
        if reaction.emoji not in role_options:
            await reaction.remove(ctx.author)

@bot.event
async def on_raw_reaction_add(payload):
    connection = connect_to_database()
    cursor = connection.cursor()
    query = "SELECT * FROM reaction_panels WHERE message_id = %s"
    values = (payload.message_id,)
    cursor.execute(query, values)
    panel_info = cursor.fetchone()

    cursor.close()
    connection.close()
    if not panel_info:
        return

    guild = bot.get_guild(panel_info[2])
    member = guild.get_member(payload.user_id)

    if member is None:
        member = await guild.fetch_member(payload.user_id)

    if panel_info[4]:  # Allow multiple roles
        role_id = emoji_role_mapping.get(str(payload.emoji))
        role = get(guild.roles, name=role_id)

        if role is not None:
            if role in member.roles:
                await member.remove_roles(role)
            else:
                await member.add_roles(role)

    else:  # Allow only one role
        await remove_other_roles(member)
        role_id = emoji_role_mapping.get(str(payload.emoji))
        if role_id:
            role = get(guild.roles, name=role_id)
            await member.add_roles(role)


@bot.event
async def on_raw_reaction_remove(payload):
    connection = connect_to_database()
    cursor = connection.cursor()
    query = "SELECT * FROM reaction_panels WHERE message_id = %s"
    values = (payload.message_id,)
    cursor.execute(query, values)
    panel_info = cursor.fetchone()
    cursor.close()
    connection.close()

    if not panel_info:
        return

    guild = bot.get_guild(panel_info[2])
    member = guild.get_member(payload.user_id)
    if member is None:
        member = await guild.fetch_member(payload.user_id)

    if panel_info[4]:  # Allow multiple roles
        role_id = emoji_role_mapping.get(str(payload.emoji))
        role = get(guild.roles, name=role_id)

        if role is not None and member is not None:
            await member.remove_roles(role)

    else:  # Allow only one role
        role_id = emoji_role_mapping.get(str(payload.emoji))
        role = get(guild.roles, name=role_id)
        if role is not None and member is not None and role.name in role_options:
            await member.remove_roles(role)

async def remove_other_roles(member):
    roles_to_remove = [role for role in member.roles if role.name in role_options]
    await member.remove_roles(*roles_to_remove)


bot.run('MTExMDI3NjU0MTc5NzEwOTc2MA.GY4aB6.5umgXl5LRHzh_LHhdMuVNAlMpgLeaXmoW4ByPY')
