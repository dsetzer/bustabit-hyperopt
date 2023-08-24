var config = {
    baseBet: { type: 'balance', label: 'Base Bet', value: 100 },
    payout: { type: 'multiplier', label: 'Payout', value: 2 },
    waitNum: { type: 'number', label: 'Wait Skips', value: 3 }
};
Object.entries(config).forEach(c=>this[c[0]]=c[1].value);

let currBet = baseBet, since = 0;

engine.on('GAME_STARTING', () => {
    if (since >= waitNum) {
        engine.bet(Math.max(100, Math.round(currBet / 100) * 100), payout);
    }
});

engine.on('GAME_ENDED', () => {
    let last = engine.history.first();
    since += (last.bust < payout) ? 1 : -since;
    if (!last.wager) return;
    if (last.cashedAt) {
        currBet = Math.max(baseBet, (currBet / (payout / (payout - 1))));
    } else {
        currBet *= payout / (payout - 1);
    }
});