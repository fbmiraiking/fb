-- Create the Standard Lens database and a dedicated application user.
-- Change the password before running this in any shared environment.
--
--   mysql -u root -p < deploy/mysql/init.sql
--
-- The backend can also create the database itself:
--   cd backend && python -m scripts.init_db

CREATE DATABASE IF NOT EXISTS `standard_lens`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

CREATE USER IF NOT EXISTS 'standard_lens'@'localhost'
    IDENTIFIED BY 'change_me';

GRANT ALL PRIVILEGES ON `standard_lens`.* TO 'standard_lens'@'localhost';

FLUSH PRIVILEGES;
