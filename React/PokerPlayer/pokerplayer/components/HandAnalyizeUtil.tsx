import type { PokerCard, PokerSuit } from "./Pokerhand";

export type PokerHandTitle =
  | "Five of a Kind"
  | "Royal Flush"
  | "Straight Flush"
  | "Four of a Kind"
  | "Full House"
  | "Flush"
  | "Straight"
  | "Three of a Kind"
  | "Two Pair"
  | "One Pair"
  | "High Card";

export type AnalyzedHand = {
  cards: readonly PokerCard[];
  title: PokerHandTitle;
};

export type HandAnalysis = {
  withJoker?: AnalyzedHand;
  withoutJoker?: AnalyzedHand;
};

type JokerCard = Extract<PokerCard, { suit: "Joker" }>;

type HandPattern = {
  ranks: readonly number[];
  score: number;
  title: PokerHandTitle;
  suit?: PokerSuit;
};

type HandCandidate = {
  cards: PokerCard[];
  score: number;
  title: PokerHandTitle;
  jokerCount: number;
  redJokerCount: number;
};

const rankValues: Record<string, number> = {
  "2": 2,
  "3": 3,
  "4": 4,
  "5": 5,
  "6": 6,
  "7": 7,
  "8": 8,
  "9": 9,
  "10": 10,
  J: 11,
  Q: 12,
  K: 13,
  A: 14,
};

const suits: readonly PokerSuit[] = ["Hearts", "Diamonds", "Clubs", "Spades"];
const suitCodes: Record<PokerSuit, number> = {
  Hearts: 0,
  Diamonds: 1,
  Clubs: 2,
  Spades: 3,
};
const scoreBase = 15 ** 5;
const kickerWeights = [15 ** 4, 15 ** 3, 15 ** 2, 15, 1] as const;

function packScore(
  category: number,
  first = 0,
  second = 0,
  third = 0,
  fourth = 0,
  fifth = 0,
): number {
  return (
    category * scoreBase +
    first * kickerWeights[0] +
    second * kickerWeights[1] +
    third * kickerWeights[2] +
    fourth * kickerWeights[3] +
    fifth
  );
}

function forEachRankCombination(
  size: number,
  visit: (combination: readonly number[]) => void,
): void {
  const combination: number[] = [];

  function choose(nextRank: number): void {
    if (combination.length === size) {
      visit(combination);
      return;
    }

    const remaining = size - combination.length;
    for (let rank = nextRank; rank <= 14 - remaining + 1; rank += 1) {
      combination.push(rank);
      choose(rank + 1);
      combination.pop();
    }
  }

  choose(2);
}

function straightRanks(high: number): number[] {
  return high === 5
    ? [14, 5, 4, 3, 2]
    : [high, high - 1, high - 2, high - 3, high - 4];
}

function buildHandPatterns(): HandPattern[] {
  const patterns: HandPattern[] = [];
  const addPattern = (
    handRanks: readonly number[],
    category: number,
    title: PokerHandTitle,
    suit?: PokerSuit,
    scoreRanks: readonly number[] = handRanks,
  ) => {
    patterns.push({
      ranks: handRanks,
      score: packScore(category, ...scoreRanks),
      title,
      suit,
    });
  };

  for (let rank = 14; rank >= 2; rank -= 1) {
    addPattern([rank, rank, rank, rank, rank], 9, "Five of a Kind");
  }

  for (const suit of suits) {
    for (let high = 14; high >= 5; high -= 1) {
      addPattern(
        straightRanks(high),
        8,
        high === 14 ? "Royal Flush" : "Straight Flush",
        suit,
        [high],
      );
    }
  }

  for (let quad = 14; quad >= 2; quad -= 1) {
    for (let kicker = 14; kicker >= 2; kicker -= 1) {
      if (kicker !== quad) {
        addPattern(
          [quad, quad, quad, quad, kicker],
          7,
          "Four of a Kind",
        );
      }
    }
  }

  for (let trips = 14; trips >= 2; trips -= 1) {
    for (let pair = 14; pair >= 2; pair -= 1) {
      if (pair !== trips) {
        addPattern(
          [trips, trips, trips, pair, pair],
          6,
          "Full House",
        );
      }
    }
  }

  for (const suit of suits) {
    forEachRankCombination(5, (combination) => {
      addPattern([...combination].reverse(), 5, "Flush", suit);
    });
  }

  for (let high = 14; high >= 5; high -= 1) {
    addPattern(straightRanks(high), 4, "Straight", undefined, [high]);
  }

  for (let trips = 14; trips >= 2; trips -= 1) {
    forEachRankCombination(2, (kickers) => {
      if (!kickers.includes(trips)) {
        const [highKicker, lowKicker] = [...kickers].reverse();
        addPattern(
          [trips, trips, trips, highKicker, lowKicker],
          3,
          "Three of a Kind",
        );
      }
    });
  }

  forEachRankCombination(2, (pairRanks) => {
    const [lowPair, highPair] = pairRanks;
    for (let kicker = 14; kicker >= 2; kicker -= 1) {
      if (kicker !== lowPair && kicker !== highPair) {
        addPattern(
          [highPair, highPair, lowPair, lowPair, kicker],
          2,
          "Two Pair",
        );
      }
    }
  });

  for (let pair = 14; pair >= 2; pair -= 1) {
    forEachRankCombination(3, (kickers) => {
      if (!kickers.includes(pair)) {
        const [highKicker, middleKicker, lowKicker] = [...kickers].reverse();
        addPattern(
          [pair, pair, highKicker, middleKicker, lowKicker],
          1,
          "One Pair",
        );
      }
    });
  }

  forEachRankCombination(5, (combination) => {
    const handRanks = [...combination].reverse();
    const isStraight =
      handRanks[0] - handRanks[4] === 4 ||
      (handRanks[0] === 14 &&
        handRanks[1] === 5 &&
        handRanks[2] === 4 &&
        handRanks[3] === 3 &&
        handRanks[4] === 2);
    if (!isStraight) {
      addPattern(handRanks, 0, "High Card");
    }
  });

  return patterns;
}

const handPatterns = buildHandPatterns();

function getMatchingCards(
  pattern: HandPattern,
  cardsByRank: readonly (readonly PokerCard[])[],
  cardsBySuitAndRank: readonly (readonly (PokerCard | undefined)[])[],
): PokerCard[] {
  const neededByRank = new Array<number>(15).fill(0);
  for (const rank of pattern.ranks) {
    neededByRank[rank] += 1;
  }

  const matches: PokerCard[] = [];
  if (pattern.suit) {
    const suitCode = suitCodes[pattern.suit];
    for (let rank = 14; rank >= 2; rank -= 1) {
      const card = cardsBySuitAndRank[suitCode][rank];
      if (neededByRank[rank] > 0 && card) {
        matches.push(card);
      }
    }
    return matches;
  }

  for (let rank = 14; rank >= 2; rank -= 1) {
    const available = cardsByRank[rank];
    const count = Math.min(neededByRank[rank], available.length);
    for (let index = 0; index < count; index += 1) {
      matches.push(available[index]);
    }
  }
  return matches;
}

function isBetterCandidate(
  candidate: HandCandidate,
  current: HandCandidate | undefined,
): boolean {
  if (!current || candidate.score !== current.score) {
    return !current || candidate.score > current.score;
  }
  if (candidate.jokerCount !== current.jokerCount) {
    return candidate.jokerCount < current.jokerCount;
  }
  return candidate.redJokerCount > current.redJokerCount;
}

function toAnalyzedHand(candidate: HandCandidate): AnalyzedHand {
  return {
    cards: candidate.cards,
    title: candidate.title,
  };
}

export function analyzePokerHand(cards: readonly PokerCard[]): HandAnalysis {
  const seenCards = new Set<string>();
  const cardsByRank: PokerCard[][] = Array.from({ length: 15 }, () => []);
  const cardsBySuitAndRank: (PokerCard | undefined)[][] = suits.map(() =>
    Array.from({ length: 15 }, () => undefined),
  );
  const jokers: JokerCard[] = [];

  for (const card of cards) {
    if (card.suit === "Joker") {
      if (card.color !== "red" && card.color !== "black") {
        throw new TypeError("Jokers must be red or black.");
      }
      const identity = `Joker:${card.color}`;
      if (seenCards.has(identity)) {
        throw new TypeError(`Duplicate card in input: ${identity}.`);
      }
      seenCards.add(identity);
      jokers.push(card);
      continue;
    }

    const rank = rankValues[card.value];
    const suitCode = suitCodes[card.suit];
    if (!Number.isInteger(rank) || !Number.isInteger(suitCode)) {
      throw new TypeError(`Invalid poker card: ${card.value} of ${card.suit}.`);
    }

    const identity = `${card.suit}:${card.value}`;
    if (seenCards.has(identity)) {
      throw new TypeError(`Duplicate card in input: ${identity}.`);
    }
    seenCards.add(identity);
    cardsByRank[rank].push(card);
    cardsBySuitAndRank[suitCode][rank] = card;
  }

  let bestWithoutJoker: HandCandidate | undefined;
  let bestWithJoker: HandCandidate | undefined;
  const preferredJoker = jokers.find((joker) => joker.color === "red") ?? jokers[0];

  for (const pattern of handPatterns) {
    const matchingCards = getMatchingCards(
      pattern,
      cardsByRank,
      cardsBySuitAndRank,
    );

    if (matchingCards.length >= 5) {
      const candidate: HandCandidate = {
        cards: matchingCards.slice(0, 5),
        score: pattern.score,
        title: pattern.title,
        jokerCount: 0,
        redJokerCount: 0,
      };
      if (isBetterCandidate(candidate, bestWithoutJoker)) {
        bestWithoutJoker = candidate;
      }
    }

    for (
      let jokerCount = 1;
      jokerCount <= Math.min(2, jokers.length);
      jokerCount += 1
    ) {
      const naturalCount = 5 - jokerCount;
      if (matchingCards.length < naturalCount) {
        continue;
      }

      const selectedJokers =
        jokerCount === 1 ? [preferredJoker] : jokers.slice(0, jokerCount);
      const redJokerCount = selectedJokers.filter(
        (joker) => joker.color === "red",
      ).length;
      const candidate: HandCandidate = {
        cards: [...matchingCards.slice(0, naturalCount), ...selectedJokers],
        score: pattern.score,
        title: pattern.title,
        jokerCount,
        redJokerCount,
      };
      if (isBetterCandidate(candidate, bestWithJoker)) {
        bestWithJoker = candidate;
      }
    }
  }

  return {
    ...(bestWithJoker ? { withJoker: toAnalyzedHand(bestWithJoker) } : {}),
    ...(bestWithoutJoker
      ? { withoutJoker: toAnalyzedHand(bestWithoutJoker) }
      : {}),
  };
}

export default analyzePokerHand;
