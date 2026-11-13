import { useMemo, useState, type FormEvent } from "react";
import {
  Box,
  Button,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import analyzePokerHand from "./HandAnalyizeUtil";
import Pokerhand, { type PokerCard } from "./Pokerhand";
import useDeckOfCards from "./useDeckOfCards";

export default function CardTable() {
  const [cardCount, setCardCount] = useState("");
  const [drawnCards, setDrawnCards] = useState<PokerCard[]>([]);
  const { remainingCards, drawCards, resetDeck } = useDeckOfCards();
  const handAnalysis = useMemo(
    () => (drawnCards.length >= 5 ? analyzePokerHand(drawnCards) : undefined),
    [drawnCards],
  );
  const count = Number(cardCount);
  const canDraw =
    cardCount.trim() !== "" &&
    Number.isSafeInteger(count) &&
    count >= 1 &&
    count < 50 &&
    count <= remainingCards;

  function handleDraw(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canDraw) {
      return;
    }

    const newlyDrawnCards = drawCards(count);
    setDrawnCards((cards) => [...cards, ...newlyDrawnCards]);
  }

  function handleReset() {
    resetDeck();
    setDrawnCards([]);
    setCardCount("");
  }

  return (
    <Stack
      component="main"
      spacing={4}
      sx={{ maxWidth: 720, minHeight: "100vh", mx: "auto", px: 2, py: 5 }}
    >
      <Box>
        <Typography component="h1" variant="h4">
          Draw cards
        </Typography>
        <Typography color="text.secondary">
          {remainingCards} cards remaining
        </Typography>
      </Box>

      <Box
        component="form"
        onSubmit={handleDraw}
        sx={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: 2 }}
      >
        <TextField
          label="Number of cards"
          type="number"
          value={cardCount}
          onChange={(event) => setCardCount(event.target.value)}
          disabled={remainingCards === 0}
          error={cardCount !== "" && !canDraw}
          helperText={
            remainingCards === 0
              ? "Reset the deck to draw more cards."
              : `Enter a whole number from 1 to ${Math.min(49, remainingCards)}.`
          }
          slotProps={{
            htmlInput: {
              min: 1,
              max: Math.min(49, remainingCards),
              step: 1,
            },
          }}
        />
        <Button type="submit" variant="contained" disabled={!canDraw}>
          Draw cards
        </Button>
        <Button
          type="button"
          variant="outlined"
          onClick={handleReset}
          disabled={remainingCards === 52 && drawnCards.length === 0}
        >
          Reset deck
        </Button>
      </Box>

      {handAnalysis ? (
        <Stack spacing={3}>
          <Stack spacing={2}>
            <Typography component="h2" variant="h5">
              Best poker hands
            </Typography>
            {handAnalysis.withJoker && (
              <Box>
                <Typography component="h3" variant="h6">
                  Best hand with a joker: {handAnalysis.withJoker.title}
                </Typography>
                <Pokerhand hand={handAnalysis.withJoker.cards} />
              </Box>
            )}
            {handAnalysis.withoutJoker && (
              <Box>
                <Typography component="h3" variant="h6">
                  Best hand without a joker: {handAnalysis.withoutJoker.title}
                </Typography>
                <Pokerhand hand={handAnalysis.withoutJoker.cards} />
              </Box>
            )}
          </Stack>
          <Divider sx={{ borderTopWidth: 4, borderColor: "text.primary" }} />
          <Box>
            <Typography component="h2" variant="h5" sx={{ mb: 2 }}>
              All drawn cards
            </Typography>
            <Pokerhand hand={drawnCards} />
          </Box>
        </Stack>
      ) : (
        drawnCards.length > 0 && <Pokerhand hand={drawnCards} />
      )}
    </Stack>
  );
}