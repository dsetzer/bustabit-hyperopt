var config = {
    baseBet: { type: 'balance', label: 'Base Bet', value: 100 },
    payout: { type: 'multiplier', label: 'Payout', value: 2 },
    waitNum: { type: 'number', label: 'Wait Skips', value: 3 }
};
Object.entries(config).forEach((c) => (globalThis[c[0]] = c[1].value));
log(config);
//log(`Script is running with baseBet: ${baseBet}, payout: ${payout}, waitNum: ${waitNum}`);
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
        currBet = baseBet;
        // log(`We won ${last.wager / 100} bits! Resetting bet to ${currBet / 100} bits`);
    } else {
        currBet *= payout / (payout - 1);
        // log(`We lost ${last.wager / 100} bits. Multiplying bet to ${currBet / 100} bits`);
    }
    // log(`Current Streak: ${since}. Balance ${userInfo.balance / 100} bits`);
});

function roundBit(bet){
    return Math.max(100, Math.round(bet / 100) * 100);
}
