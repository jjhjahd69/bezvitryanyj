-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Хост: my-mysql
-- Час створення: Квт 04 2025 р., 17:32
-- Версія сервера: 9.2.0
-- Версія PHP: 8.2.28

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- База даних: `viter`
--

-- --------------------------------------------------------

--
-- Структура таблиці `games`
--

CREATE TABLE `games` (
  `id` int NOT NULL,
  `gamename` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `gamedescription` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `gametype` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `gamecreatorid` bigint DEFAULT NULL,
  `gamemasters` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `gameplayers` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `gamestatus` int DEFAULT NULL,
  `gamecreationdate` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- --------------------------------------------------------

--
-- Структура таблиці `responses`
--

CREATE TABLE `responses` (
  `id` int NOT NULL,
  `receiver` bigint DEFAULT NULL,
  `writer` bigint DEFAULT NULL,
  `type` text CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `gameid` int DEFAULT NULL,
  `text` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `rate` int DEFAULT NULL,
  `date` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

-- --------------------------------------------------------

--
-- Структура таблиці `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `userid` bigint DEFAULT NULL,
  `adminresponse` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `balance` int DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci,
  `image` mediumtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Індекси збережених таблиць
--

--
-- Індекси таблиці `games`
--
ALTER TABLE `games`
  ADD PRIMARY KEY (`id`);

--
-- Індекси таблиці `responses`
--
ALTER TABLE `responses`
  ADD PRIMARY KEY (`id`);

--
-- Індекси таблиці `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT для збережених таблиць
--

--
-- AUTO_INCREMENT для таблиці `games`
--
ALTER TABLE `games`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT для таблиці `responses`
--
ALTER TABLE `responses`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT для таблиці `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
