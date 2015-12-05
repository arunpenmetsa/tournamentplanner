-- Table definitions for the tournament project.
--

-- Initial clean up. drop the database
DROP DATABASE IF EXISTS tournament;

-- Create the tournament database
CREATE DATABASE tournament;

-- Connect to the database
\c tournament;

-- Create the players table
-- This table reflects the record of a player at any point
-- It tracks the name, wins, byes, opponent match wins and matches
create table players(
	playerID serial primary key,
	name text,
	wins integer,
	byes integer check (byes < 2),
	omw integer,	
	matches integer	
);

-- Create the matches table
-- This has the record of all matches in the tournament so far
-- The 'opponent' or player2ID can be 0 in case of a bye
-- Consequently, the column does not reference players
-- Another method would be to create a null player with ID 0 in the players table
-- The result is stored as 2 for player1ID win, 1 for draw, 0 for player1ID loss
create table matches(
	matchID serial primary key,
	player1ID serial references players,
	player2ID serial,
	result integer	
);

-- Create view to compute opponent match wins
-- For each player, take all the opponents as recorded in the matches table
-- and sum their wins. Join the opponent column (player2ID) with players
-- to get the match wins. 
-- Note that for this to work, each match has to be entered twice into the 
-- matches table. This will ensure that a vs b is recorded for both players
-- a and b. The match is entered as a vs b and b vs a. 
create view omw as (
	SELECT
		matches.player1ID as id,
		coalesce(sum(players.wins),0) as omw
		from matches left outer join players
		on matches.player2ID = players.playerID
		group by matches.player1ID 

);



