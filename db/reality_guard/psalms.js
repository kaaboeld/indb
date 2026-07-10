// Psalm 23 - The Lord is my Shepherd (King James Version)
const PSALM_23 = [
    "The LORD is my shepherd; I shall not want.",
    "He maketh me to lie down in green pastures:",
    "he leadeth me beside the still waters.",
    "He restoreth my soul:",
    "he leadeth me in the paths of righteousness for his name's sake.",
    "Yea, though I walk through the valley of the shadow of death,",
    "I will fear no evil: for thou art with me;",
    "thy rod and thy staff they comfort me.",
    "Thou preparest a table before me in the presence of mine enemies:",
    "thou anointest my head with oil; my cup runneth over.",
    "Surely goodness and mercy shall follow me all the days of my life:",
    "and I will dwell in the house of the LORD for ever."
];

// Psalm 91 - Protection
const PSALM_91 = [
    "He that dwelleth in the secret place of the most High",
    "shall abide under the shadow of the Almighty.",
    "I will say of the LORD, He is my refuge and my fortress:",
    "my God; in him will I trust.",
    "Surely he shall deliver thee from the snare of the fowler,",
    "and from the noisome pestilence.",
    "He shall cover thee with his feathers,",
    "and under his wings shalt thou trust:",
    "his truth shall be thy shield and buckler."
];

// Psalm 1 - Blessed is the man
const PSALM_1 = [
    "Blessed is the man that walketh not in the counsel of the ungodly,",
    "nor standeth in the way of sinners,",
    "nor sitteth in the seat of the scornful.",
    "But his delight is in the law of the LORD;",
    "and in his law doth he meditate day and night.",
    "And he shall be like a tree planted by the rivers of water,",
    "that bringeth forth his fruit in his season;",
    "his leaf also shall not wither;",
    "and whatsoever he doeth shall prosper."
];

const ALL_VERSES = [...PSALM_23, ...PSALM_91, ...PSALM_1];

module.exports = { PSALM_23, PSALM_91, PSALM_1, ALL_VERSES };
