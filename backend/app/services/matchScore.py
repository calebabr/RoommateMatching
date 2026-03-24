import math

class matchScore:
    def __init__(self):
        self.categoryRange = {
            "sleepScheduleWeekdays": [24, 0.125],
            "sleepScheduleWeekends": [24, 0.125],
            "cleanliness": [10, 0.2],
            "noiseTolerance": [10, 0.2],
            "guests": [10, 1.0],
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