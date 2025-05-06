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
                sql_query = "SELECT 1 FROM users WHERE userid = %s LIMIT 1"
                query_params = (member.id,)
                await cursor.execute(sql_query, query_params)
                user_exist = await cursor.fetchone()

                return user_exist

    @db_operation
    async def add_user_to_database(self, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = """
                            INSERT INTO users (userid, adminresponse, balance, description, image)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                query_params = (member.id, "Відсутні", 0, "Опис профілю не встановлений.", None,)
                await cursor.execute(sql_query, query_params)

    @db_operation
    async def get_user(self, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "SELECT * FROM users WHERE userid = %s"
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
                sql_query = "UPDATE responses SET image = %s WHERE userid = %s"
                query_params = (image_link, interaction.user.id,)
                await cursor.execute(sql_query, query_params)
                                   

    @db_operation
    async def set_user_description(self, text, interaction):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "UPDATE users SET description = %s WHERE userid = %s"
                query_params = (text, interaction.user.id, )
                await cursor.execute(sql_query, query_params)

    @db_operation
    async def set_user_adminresponse(self, text, member):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql_query = "UPDATE users SET adminresponse = %s WHERE userid = %s"
                query_params = (text, member.id, )
                await cursor.execute(sql_query, query_params)