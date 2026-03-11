# database.py
import mysql.connector
from mysql.connector import pooling, Error
from flask import g
import logging

logger = logging.getLogger(__name__)
_pool = None


def init_db(app):
    global _pool
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="smart_interview_pool",
            pool_size=app.config["MYSQL_POOL_SIZE"],
            host=app.config["MYSQL_HOST"],
            port=app.config["MYSQL_PORT"],
            user=app.config["MYSQL_USER"],
            password=app.config["MYSQL_PASSWORD"],
            database=app.config["MYSQL_DATABASE"],
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
            connect_timeout=10,
        )
        logger.info("MySQL pool created.")
    except Error as e:
        logger.error("Pool creation failed: %s", e)
        raise


def get_db():
    if "db" not in g:
        if _pool is None:
            raise RuntimeError("Database pool not initialised.")
        try:
            g.db = _pool.get_connection()
        except Error as e:
            logger.error("Connection error: %s", e)
            raise
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None and db.is_connected():
        if error:
            db.rollback()
        db.close()


def execute_query(query, params=(), fetch=False):
    conn = get_db()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        conn.rollback()
        logger.error("Query failed: %s", e)
        raise
    finally:
        if cursor:
            cursor.close()