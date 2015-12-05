#!/usr/bin/env python
# 
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2
import math


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def deleteMatches():
    """delete all the matches in the system
  
    This clears the matches table and sets the number of matches, wins, omw, byes to 0
    in the players table
    """    
    DB = connect()
    c = DB.cursor()
    c.execute("delete from matches")
    c.execute("UPDATE players set (wins, byes, omw, matches) = (0, 0, 0, 0)")
    DB.commit()
    DB.close()


def deletePlayers():
    """delete all the players in the system
  
    This clears the matches table and the players table
    """  
    deleteMatches()    
    DB = connect()
    c = DB.cursor()
    c.execute("delete from players")
    DB.commit()
    DB.close()


def countPlayers():
    """Counts number of players in the system"""      
    DB = connect()
    c = DB.cursor()
    c.execute("select count(*) as num from players")
    count = c.fetchall()[0][0]
    DB.close()
    return count


def registerPlayer(name):
    """Adds a player to the tournament database.
  
    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)
  
    Args:
      name: the player's full name (need not be unique).
    """
    DB = connect()
    c = DB.cursor()
    c.execute("INSERT into players (playerID, name, wins, byes, omw, matches) values (DEFAULT, %s, 0, 0, 0, 0)", (name,))
    DB.commit()
    DB.close()


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a player
    tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, byes, omw, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        byes: number of byes the player has received
        omw: number of matches opponent has won
        matches: the number of matches the player has played
    """
    updateOMW()

    DB = connect()
    c = DB.cursor()
    c.execute("select * from players order by wins desc, omw desc, byes desc, matches desc")
    rows = c.fetchall()
    DB.close()
    return rows


def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    DB = connect()
    c = DB.cursor()

    # Record the match from the winner point of view
    c.execute("INSERT into matches (matchID, player1ID, player2ID, result) values (DEFAULT, %s, %s, 2)", (winner, loser))
    c.execute("UPDATE players set (wins, matches) = (wins+1, matches+1) where playerID = %s", (winner,))

    # Check to make sure it is not a bye
    if loser <> 0:
        # Record match from loser point of view
        c.execute("INSERT into matches (matchID, player1ID, player2ID, result) values (DEFAULT, %s, %s, 0)", (loser, winner))
        c.execute("UPDATE players set matches = matches+1 where playerID = %s", (loser,))
    else:
        # Record the bye for the winner
        c.execute("UPDATE players set byes = byes+1 where playerID = %s", (winner,))

    DB.commit()
    DB.close()    
 

def swissPairings():
    """Returns a list of pairs of players for the next round of a match.
  
    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings. 

    If there an odd number of players, then one player receives a bye
  
    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    updateOMW()

    DB = connect()
    c = DB.cursor()

    # Get the list of players sorted by wins, then opponent winning percentage, then byes, then matches
    # Since byes is before matches, the player with bye will not be at the end and will not receive a second bye
    query = """
            select playerID, name 
            from players left join omw
            on players.playerID = omw.id
            order by players.wins desc, omw.omw desc, players.byes desc, players.matches desc
            """
    c.execute(query)
    players = c.fetchall()

    numPlayers = len(players)
    count = 0

    if numPlayers < 1:
        raise ValueError("No Players Registered")

    # Build the next round of matches
    nextRound = []
    while numPlayers > 1:
        (pid1, pname1) = players[0]
        #print ("Checking player",pid1)

        # Select players you have not played against and order by byes and matches
        # This gives the oppononents that could be matches. This is the valid list
        query = """
                select playerid, name from players where playerid not in 
                (select player2ID from matches where player1ID = %s) and playerid <> %s
                order by wins desc, byes desc, matches desc
                """
        c.execute(query,(str(pid1),str(pid1)))
        validList = c.fetchall()  

        count = 0;
        match = 0
        # Go through the player list and find the next player that is in the valid list and pair them
        # Remove the pair from the player list and keep going
        while count < numPlayers-1 and match is 0:
            (pid2, pname2) = players[count+1]
            if (pid2, pname2) in validList:
                #print ("pairing with ", pid2)
                pairing = (pid1, pname1, pid2, pname2)
                nextRound += (pairing,)
                players.remove((pid1, pname1))
                players.remove((pid2, pname2))
                match = 1
            else:
                count = count + 1

        # If you reach the end and there is no valid player, this means that you have played
        # with every player. Pick the next player. This should never happen 
        if count is numPlayers-1 and match is 0:
            (pid2, pname2) = players[count]
            #print ("All players played: pairing with ", pid2)
            pairing = (pid1, pname1, pid2, pname2)
            nextRound += (pairing,)
            players.remove((pid1, pname1))
            players.remove((pid2, pname2))
        numPlayers = len(players)
    
    # There are an odd number of players. Allocate a bye
    if numPlayers > 0:
        #print "Odd Number of players"
        (pid1, pname1) = players[count]
        pairing = (pid1, pname1, 0, "")
        nextRound += (pairing,)

    DB.commit()
    DB.close()
    return nextRound


def updateOMW():
    """Update the omw for all the players"""      
    DB = connect()
    c = DB.cursor()

    query = """
            UPDATE players set omw = omw.omw  
            from omw where players.playerID = omw.id
            """    
    c.execute(query)
    DB.commit()
    DB.close()   



