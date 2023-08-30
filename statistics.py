class Statistics:
    def __init__(self):
        self.duration = 0
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.balance_ath = starting_balance
        self.balance_atl = starting_balance
        self.games_total = 0
        self.games_played = 0
        self.game_skipped = 0
        self.games_won = 0
        self.games_lost = 0
        self.profit = 0
        self.lowest_bet = 0
        self.highest_bet = 0
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

    def update(self, game):
        self.games_total += 1
        if game['wager'] is not None:
            self.games_played += 1
            duration += Math.log(config.targetPayout.value) / 0.00006
            self.total_wagered += game['wager']

            if game['wager'] < self.lowest_bet:
                self.lowest_bet = game['wager']
            elif game['wager'] > self.highest_bet:
                self.highest_bet = game['wager']

            if game['cashedAt'] is not None:
                self.games_won += 1
                winnings = game['wager'] * game['cashedAt']
                self.total_won += winnings
                self.balance += winnings
                self.since_last_win = 0
                self.since_last_lose += 1
                self.streak_gain += winnings
                if self.since_last_lose > self.longest_win_streak:
                    self.longest_win_streak = self.since_last_lose
                    self.longest_streak_gain = self.streak_gain
            else:
                self.games_lost += 1
                self.total_lost += game['wager']
                self.balance -= game['wager']
                self.since_last_win += 1
                self.since_last_lose = 0
                self.streak_cost += game['wager']
                if self.since_last_win > self.longest_lose_streak:
                    self.longest_lose_streak = self.since_last_win
                    self.longest_streak_cost = self.streak_cost
        else:
            self.game_skipped += 1

        if self.balance > self.balance_ath:
            self.balance_ath = self.balance
        elif self.balance < self.balance_atl:
            self.balance_atl = self.balance

        self.profit = self.balance - self.starting_balance
        if self.profit > self.profit_ath:
            self.profit_ath = self.profit
        elif self.profit < self.profit_atl:
            self.profit_atl = self.profit

        self.profit_per_hour = self.profit / (self.duration / 3600)


    def __str__(self):
        # print the statistics
        return f"""
        Starting balance: {self.starting_balance}
        Ending balance: {self.balance}
        Balance all time high: {self.balance_ath}
        Balance all time low: {self.balance_atl}
        Games total: {self.games_total}
        Games played: {self.games_played}
        Games skipped: {self.game_skipped}
        Games won: {self.games_won}
        Games lost: {self.games_lost}
        Profit: {self.profit}
        Lowest bet: {self.lowest_bet}
        Highest bet: {self.highest_bet}
        Longest win streak: {self.longest_win_streak}
        Longest streak gain: {self.longest_streak_gain}
        Longest lose streak: {self.longest_lose_streak}
        Longest streak cost: {self.longest_streak_cost}
        Profit per hour: {self.profit_per_hour}
        Profit all time high: {self.profit_ath}
        Profit all time low: {self.profit_atl}
        Total wagered: {self.total_wagered}
        Total won: {self.total_won}
        Total lost: {self.total_lost}
        """
