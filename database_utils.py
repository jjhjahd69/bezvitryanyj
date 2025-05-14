# database_utils.py
import discord
from discord.ext import commands
from discord import app_commands
import aiomysql
from config import *
import logging

class DatabaseFuncs:
    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool

        if self.pool is None:
            logging.critical("!!! DatabaseFuncs ініціалізовано без активного db_pool! Це призведе до помилок.")


    def db_operation(method):
        async def wrapper(self_instance, *args, **kwargs): # self_instance - це екземпляр DatabaseFuncs
            if not self_instance.pool:
                logging.error(f"Метод '{method.__name__}' не може бути виконаний: pool недоступний.")
                if method_to_wrap.__name__ == "get_user_rating_average":
                    return None, None # Повертаємо кортеж з None
                return None
            try:
                result = await method(self_instance, *args, **kwargs)
                return result

            except aiomysql.Error as db_err:
                logging.error(f"Помилка бази даних: {db_err}")
                return None
            
            except Exception as e:
                # Обробка інших можливих помилок
                logging.error(f"Інша помилка: {e}")
                return None

        return wrapper
    
    @db_operation
    async def check_user_exist(self, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "SELECT 1 FROM users WHERE user_id = %s LIMIT 1"
                query_params = (member.id,)
                await cursor.execute(sql_query, query_params)
                user_exist = await cursor.fetchone()

                return user_exist

    @db_operation
    async def add_user_to_database(self, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = """
                            INSERT INTO users (user_id)
                            VALUES (%s)
                        """
                query_params = (member.id, )
                await cursor.execute(sql_query, query_params)

    @db_operation
    async def get_user(self, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "SELECT * FROM users WHERE user_id = %s"
                query_params = (member.id,)
                await cursor.execute(sql_query, query_params)
                user_info = await cursor.fetchone()

                return user_info

    @db_operation
    async def get_user_rating_average(self, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute('SELECT AVG(rate) AS avg_rate FROM responses WHERE receiver = %s AND type = %s', (member.id, 2))
                playerrate_dict = await cursor.fetchone()
                await cursor.execute('SELECT AVG(rate) AS avg_rate FROM responses WHERE receiver = %s AND type = %s', (member.id, 1))
                masterrate_dict = await cursor.fetchone()
                
                return playerrate_dict, masterrate_dict

    @db_operation
    async def set_user_image(self, image_link, interaction):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "UPDATE users SET image = %s WHERE user_id = %s"
                query_params = (image_link, interaction.user.id,)
                await cursor.execute(sql_query, query_params)
                                   

    @db_operation
    async def set_user_description(self, text, interaction):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "UPDATE users SET description = %s WHERE user_id = %s"
                query_params = (text, interaction.user.id, )
                await cursor.execute(sql_query, query_params)

    @db_operation
    async def set_user_adminresponse(self, text, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "UPDATE users SET admin_response = %s WHERE userid = %s"
                query_params = (text, member.id, )
                await cursor.execute(sql_query, query_params)

    @db_operation
    async def get_game_info(self, game_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "SELECT * FROM games WHERE id = %s"
                query_params = (game_id,)
                await cursor.execute(sql_query, query_params)
                game_data = await cursor.fetchone()

                return game_data

    @db_operation
    async def set_game_status(self, status, game_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.Cursor) as cursor:
                sql_query = "UPDATE games SET status = %s WHERE id = %s"
                query_params = (status.value, game_id, )
                await cursor.execute(sql_query, query_params)

    @db_operation
    async def delete_game(self, game_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.Cursor) as cursor:
                await cursor.execute("DELETE FROM games WHERE id = %s", (game_id,))

    @db_operation
    async def create_game(self, game_name, game_description, game_type, creator_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.Cursor) as cursor:
                sql = """
                    INSERT INTO games
                    (name, description, type, creator_id)
                    VALUES (%s, %s, %s, %s)
                """
                query_params = (
                    game_name, game_description, game_type, creator_id, 
                )

                await cursor.execute(sql, query_params)
                logging.debug(f"LASTROWID {cursor.lastrowid}")
    
                return cursor.lastrowid

    @db_operation
    async def get_game_participants(self, game_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.Cursor) as cursor:
                await cursor.execute(
                    "SELECT user_id FROM game_participants WHERE role = %s AND game_id = %s",
                    (1, game_id))
                    
                masters = [row[0] for row in await cursor.fetchall()]

                await cursor.execute(
                    "SELECT user_id FROM game_participants WHERE role = %s AND game_id = %s", 
                    (2, game_id))

                players = [row[0] for row in await cursor.fetchall()]

                return masters, players
