import math

class matchScore:
    def __init__(self):
        self.categoryRange = {
            "sleepScheduleWeekdays": [24, 0.125],
            "sleepScheduleWeekends": [24, 0.125],
            "cleanliness": [10, 0.2],
            "noiseTolerance": [10, 0.2],
            "guests": [10, 1.0],
            "personality": [10, 0.2],
            "smoking": [10, 0.1],
            "sharedSpace": [10, 0.2],
            "communication": [10, 0.2],
        }
        # P3FT.11 — human-readable labels for the score breakdown endpoint.
        # Display metadata only; it does not affect scoring.
        self.categoryLabels = {
            "sleepScheduleWeekdays": "Sleep Schedule (Weekdays)",
            "sleepScheduleWeekends": "Sleep Schedule (Weekends)",
            "cleanliness": "Cleanliness",
            "noiseTolerance": "Noise Tolerance",
            "guests": "Guests",
            "personality": "Personality",
            "smoking": "Smoking",
            "sharedSpace": "Shared Space",
            "communication": "Communication",
        }

    def genderCompatible(self, user1, user2) -> bool:
        """
        Checks if two users have matching genders.
        Males can only match with males, females only with females.
        """
        g1 = user1.get("gender", "").lower()
        g2 = user2.get("gender", "").lower()
        # If either user has no gender set, allow matching (backwards compat)
        if not g1 or not g2:
            return True
        return g1 == g2

    def dealBreak(self, category, user1, user2) -> float:
        if (user1[category][1] or user2[category][1]) and math.fabs(user1[category][0] - user2[category][0]) > self.categoryRange[category][0] * self.categoryRange[category][1]:
            return 0.0
        return 1.0

    def preferenceScore(self, category, cat1, cat2) -> float:
        catRange = self.categoryRange[category][0]
        return 1.0 - math.pow((abs(cat1 - cat2) / catRange), 2)

    def matchScore(self, user1, user2) -> float:
        # Gender check first — incompatible genders = 0 score
        if not self.genderCompatible(user1, user2):
            return 0.0

        for c in self.categoryRange.keys():
            if self.dealBreak(c, user1, user2) == 0.0:
                return 0.0

        weightedSum = 0.0
        for c in self.categoryRange.keys():
            weightedSum += self.preferenceScore(c, user1[c][0], user2[c][0])
        return weightedSum / len(self.categoryRange.keys())

    def compatibilityScore(self, user1, user2) -> float:
        # Gender check — incompatible genders = 0 score
        if not self.genderCompatible(user1, user2):
            return 0.0
        return min(self.matchScore(user1, user2), self.matchScore(user2, user1))

    # --- P3FT.11: per-category breakdown -----------------------------------

    # Normalized-distance thresholds used to bucket how far apart two users are
    # on a single category.  Buckets exist so the endpoint never has to leak the
    # other user's raw preference value.
    SAME_THRESHOLD = 0.05
    CLOSE_THRESHOLD = 0.25

    def differenceBucket(self, category, cat1, cat2) -> str:
        """Bucket the gap between two values as 'same' / 'close' / 'different'."""
        catRange = self.categoryRange[category][0]
        delta = abs(cat1 - cat2) / catRange
        if delta <= self.SAME_THRESHOLD:
            return "same"
        if delta <= self.CLOSE_THRESHOLD:
            return "close"
        return "different"

    def categoryBreakdown(self, user1, user2) -> list:
        """Explain `compatibilityScore(user1, user2)` one category at a time.

        `user1` is the *viewer*: `yourValue` is always their own raw value.  The
        other user's value is never returned — only the bucketed `difference`.
        Each per-category `score` is the minimum of `preferenceScore` evaluated
        in both directions, matching how `compatibilityScore` takes the min of
        the two `matchScore` directions.
        """
        rows = []
        for c in self.categoryRange.keys():
            v1 = user1[c][0]
            v2 = user2[c][0]
            score = min(
                self.preferenceScore(c, v1, v2),
                self.preferenceScore(c, v2, v1),
            )
            rows.append({
                "key": c,
                "label": self.categoryLabels[c],
                "yourValue": v1,
                "difference": self.differenceBucket(c, v1, v2),
                "score": round(score, 6),
                "isDealBreaker": bool(user1[c][1] or user2[c][1]),
                "dealBreakerTriggered": self.dealBreak(c, user1, user2) == 0.0,
            })
        return rows