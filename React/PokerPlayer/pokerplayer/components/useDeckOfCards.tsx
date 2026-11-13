import { useCallback, useRef, useState } from "react";
import type { PokerCard, PokerSuit } from "./Pokerhand";

const suits: readonly PokerSuit[] = ["Hearts", "Diamonds", "Clubs", "Spades"];
const values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"];

function createDeck(): PokerCard[] {
  const standardCards = suits.flatMap((suit) =>
    values.map((value) => ({ value, suit })),
  );

  return [
    ...standardCards,
    { value: "Joker", suit: "Joker", color: "red" },
    { value: "Joker", suit: "Joker", color: "black" },
  ];
}

function shuffled<T>(cards: readonly T[]): T[] {
  const result = [...cards];

  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }

  return result;
}

export default function useDeckOfCards() {
  const [deck, setDeck] = useState<PokerCard[]>(() => shuffled(createDeck()));
  const deckRef = useRef(deck);

  const updateDeck = useCallback((nextDeck: PokerCard[]) => {
    deckRef.current = nextDeck;
    setDeck(nextDeck);
  }, []);

  const drawCards = useCallback(
    (count: number): PokerCard[] => {
      if (!Number.isInteger(count) || count < 0) {
        throw new RangeError("Card count must be a non-negative integer.");
      }

      const drawn = deckRef.current.slice(0, count);
      if (drawn.length > 0) {
        updateDeck(deckRef.current.slice(drawn.length));
      }
      return drawn;
    },
    [updateDeck],
  );

  const drawCard = useCallback(() => drawCards(1)[0], [drawCards]);
  const shuffleDeck = useCallback(
    () => updateDeck(shuffled(deckRef.current)),
    [updateDeck],
  );
  const resetDeck = useCallback(
    () => updateDeck(shuffled(createDeck())),
    [updateDeck],
  );

  return {
    deck,
    remainingCards: deck.length,
    drawCard,
    drawCards,
    shuffleDeck,
    resetDeck,
  };
}