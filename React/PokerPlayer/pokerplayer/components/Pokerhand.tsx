import { Card, CardContent, Stack, Typography } from "@mui/material";

export type PokerSuit = "Hearts" | "Diamonds" | "Clubs" | "Spades";

export type PokerCard =
  | {
      value: string;
      suit: PokerSuit;
    }
  | {
      value: "Joker";
      suit: "Joker";
      color: "red" | "black";
    };

export type PokerHand = readonly PokerCard[];

const suitSymbols: Record<PokerSuit, string> = {
  Hearts: "♥",
  Diamonds: "♦",
  Clubs: "♣",
  Spades: "♠",
};

type PokerhandProps = {
  hand: PokerHand;
};

export default function Pokerhand({ hand }: PokerhandProps) {
  return (
    <Stack
      direction="row"
      spacing={2}
      useFlexGap
      sx={{ flexWrap: "wrap", justifyContent: "center" }}
    >
      {hand.map((card) => {
        const isJoker = card.suit === "Joker";
        const color = isJoker
          ? card.color === "red"
            ? "#d32f2f"
            : "#212121"
          : card.suit === "Hearts" || card.suit === "Diamonds"
            ? "#d32f2f"
            : "#212121";

        return (
          <Card
            key={`${card.value}-${card.suit}-${isJoker ? card.color : ""}`}
            variant="outlined"
            aria-label={
              isJoker ? `${card.color} joker` : `${card.value} of ${card.suit}`
            }
            sx={{
              width: 96,
              textAlign: "center",
              ...(isJoker ? { borderColor: color } : {}),
            }}
          >
            <CardContent>
              <Typography variant="h5" sx={isJoker ? { color } : undefined}>
                {card.value}
              </Typography>
              <Typography
                component="span"
                aria-hidden="true"
                sx={{
                  color,
                  fontFamily: '"Segoe UI Symbol", "Segoe UI Emoji", sans-serif',
                  fontSize: "2rem",
                  lineHeight: 1,
                }}
              >
                {isJoker ? "🃏" : suitSymbols[card.suit]}
              </Typography>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}