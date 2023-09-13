import math

class Statistics:
    def __init__(self, initial_balance):
        self.duration = 0
        self.starting_balance = initial_balance
        self.balance = initial_balance
        self.balance_ath = initial_balance
        self.balance_atl = initial_balance
        self.games_total = 0
        self.games_played = 0
        self.game_skipped = 0
        self.games_won = 0
        self.games_lost = 0
        self.profit = 0
        self.lowest_bet = float('inf')
        self.highest_bet = float('-inf')
        self.longest_win_streak = 0
        self.longest_streak_gain = 0
        self.since_last_win = 0
        self.since_last_lose = 0
        self.longest_lose_streak = 0
        self.longest_streak_cost = 0
        self.streak_cost = 0
        self.streak_gain = 0
        self.profit_per_hour = 0
        self.profit_ath = 0
        self.profit_atl = 0
        self.total_wagered = 0
        self.total_won = 0
        self.total_lost = 0

    def update(self, engine):
        lastGame = engine.history.first()
        self.games_total += 1
        self.duration += math.log(lastGame['bust']) / 0.00006  # Assuming targetPayout is available in engine
        if lastGame['wager'] is not None:
            self.games_played += 1
            # update userinfo stats
            engine._userInfo.wagers += 1
            engine._userInfo.wagered += lastGame['wager']
            # update stats
            self.total_wagered += lastGame['wager']
            if lastGame['wager'] < self.lowest_bet:
                self.lowest_bet = lastGame['wager']
            elif lastGame['wager'] > self.highest_bet:
                self.highest_bet = lastGame['wager']

            if lastGame['cashedAt'] is not None:
                # update userinfo stats
                engine._userInfo.profit += (lastGame['wager'] * (lastGame['cashedAt'] - 1))
                # update stats
                self.games_won += 1
                winnings = lastGame['wager'] * lastGame['cashedAt']
                self.total_won += winnings
                self.balance += winnings
                self.since_last_win = 0
                self.since_last_lose += 1
                self.streak_gain += winnings
                if self.since_last_lose > self.longest_win_streak:
                    self.longest_win_streak = self.since_last_lose
                    self.longest_streak_gain = self.streak_gain
            else:
                # update userinfo stats
                engine._userInfo.profit -= lastGame['wager']
                # update stats
                self.games_lost += 1
                self.total_lost += lastGame['wager']
                self.balance -= lastGame['wager']
                self.since_last_win += 1
                self.since_last_lose = 0
                self.streak_cost += lastGame['wager']
                if self.since_last_win > self.longest_lose_streak:
                    self.longest_lose_streak = self.since_last_win
                    self.longest_streak_cost = self.streak_cost

            if self.balance > self.balance_ath:
                self.balance_ath = self.balance
            elif self.balance < self.balance_atl:
                self.balance_atl = self.balance

            self.profit = self.balance - self.starting_balance
            if self.profit > self.profit_ath:
                self.profit_ath = self.profit
            elif self.profit < self.profit_atl:
                self.profit_atl = self.profit
        else:
            self.game_skipped += 1

        # print(self.duration, self.profit)
        self.profit_per_hour = self.profit / (self.duration / 3600)
 
    def get_metric(self):
        # return the optmization metric used for the objective function
        # it must consider the following: profit, wagered, games played, balance, balance_ath, balance_atl, profit_ath, profit_atl
        return self.profit
    
    def get_statistics(self):
        return {
            'starting_balance': self.starting_balance,
            'balance': self.balance,
            'balance_ath': self.balance_ath,
            'balance_atl': self.balance_atl,
            'games_total': self.games_total,
            'games_played': self.games_played,
            'game_skipped': self.game_skipped,
            'games_won': self.games_won,
            'games_lost': self.games_lost,
            'profit': self.profit,
            'lowest_bet': self.lowest_bet,
            'highest_bet': self.highest_bet,
            'longest_win_streak': self.longest_win_streak,
            'longest_streak_gain': self.longest_streak_gain,
            'longest_lose_streak': self.longest_lose_streak,
            'longest_streak_cost': self.longest_streak_cost,
            'profit_per_hour': self.profit_per_hour,
            'profit_ath': self.profit_ath,
            'profit_atl': self.profit_atl,
            'total_wagered': self.total_wagered,
            'total_won': self.total_won,
            'total_lost': self.total_lost
        }