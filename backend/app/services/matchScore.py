import math

class matchScore:
    def __init__(self):
        # Each entry: [range, dealbreaker_threshold_fraction, weight]
        # Weights are derived from Auburn survey data:
        #   - cleanliness: 87% of students listed it as a top trait → highest weight
        #   - noise/respect: 24-25% mentioned it → moderate weight
        #   - sleep schedule: 15% mentioned it → moderate weight
        #   - personality: 27% described social style, 59% want a close friend → significant weight
        #   - smoking/substances: 7% hard dealbreaker → lower weight but dealbreaker-heavy
        #   - guests: 10% mentioned it → lower weight
        #   - shared space / boundaries: 7% mentioned it → lower weight
        #   - communication: 10% mentioned it → moderate weight
        self.categoryRange = {
            "sleepScheduleWeekdays": [24, 0.125, 1.0],
            "sleepScheduleWeekends": [24, 0.125, 0.8],
            "cleanliness": [10, 0.2, 2.5],
            "noiseTolerance": [10, 0.2, 1.3],
            "guests": [10, 1.0, 0.8],
            "personality": [10, 0.3, 1.5],
            "smoking": [10, 0.2, 1.2],
            "sharedSpace": [10, 0.3, 0.7],
            "communication": [10, 0.3, 1.0],
        }

        # Weight given to lifestyle tag overlap (added as bonus on top of preference score)
        self.tagBonusWeight = 0.10

    def dealBreak(self, category, user1, user2) -> float:
        """
        Checks if a preference difference between two users is a dealbreaker.

        Parameters:
            category (str): The preference category to check.
            user1 (dict): First user's preference data.
            user2 (dict): Second user's preference data.

        Returns:
            float: 0.0 if the difference is a dealbreaker, 1.0 otherwise.
        """
        catRange = self.categoryRange[category][0]
        threshold = self.categoryRange[category][1]
        if (user1[category][1] or user2[category][1]) and math.fabs(user1[category][0] - user2[category][0]) > catRange * threshold:
            return 0.0
        return 1.0

    def preferenceScore(self, category, cat1, cat2) -> float:
        """
        Calculates a compatibility score for a specific preference category between two values.

        Parameters:
            category (str): The preference category being compared.
            cat1 (float): First user's preference value.
            cat2 (float): Second user's preference value.

        Returns:
            float: A compatibility score from 0.0 to 1.0, where 1.0 is perfect match.
        """
        catRange = self.categoryRange[category][0]
        return 1.0 - math.pow((abs(cat1 - cat2) / catRange), 2)

    def lifestyleTagBonus(self, user1, user2) -> float:
        """
        Calculates a Jaccard similarity bonus based on shared lifestyle tags.

        Parameters:
            user1 (dict): First user's profile (must include 'lifestyleTags' key).
            user2 (dict): Second user's profile (must include 'lifestyleTags' key).

        Returns:
            float: Jaccard similarity from 0.0 to 1.0. Returns 0.0 if both tag lists are empty.
        """
        tags1 = set(t.lower().strip() for t in user1.get("lifestyleTags", []))
        tags2 = set(t.lower().strip() for t in user2.get("lifestyleTags", []))
        if not tags1 and not tags2:
            return 0.0
        union = tags1 | tags2
        if not union:
            return 0.0
        return len(tags1 & tags2) / len(union)

    def matchScore(self, user1, user2) -> float:
        """
        Calculates the overall match score from user1's perspective to user2.
        Uses survey-derived per-category weights instead of equal weighting.

        Parameters:
            user1 (dict): First user's preference object.
            user2 (dict): Second user's preference object.

        Returns:
            float: Match score from 0.0 to 1.0. Returns 0.0 if any dealbreaker exists.
        """
        for c in self.categoryRange.keys():
            if self.dealBreak(c, user1, user2) == 0.0:
                return 0.0

        weightedSum = 0.0
        totalWeight = 0.0
        for c in self.categoryRange.keys():
            weight = self.categoryRange[c][2]
            weightedSum += self.preferenceScore(c, user1[c][0], user2[c][0]) * weight
            totalWeight += weight

        preferenceResult = weightedSum / totalWeight

        tagBonus = self.lifestyleTagBonus(user1, user2) * self.tagBonusWeight
        return min(preferenceResult + tagBonus, 1.0)

    def compatibilityScore(self, user1, user2) -> float:
        """
        Calculates the mutual compatibility score between two users (symmetric).

        Parameters:
            user1 (dict): First user's preference object.
            user2 (dict): Second user's preference object.

        Returns:
            float: The minimum of both directional match scores (0.0 to 1.0).
        """
        return min(self.matchScore(user1, user2), self.matchScore(user2, user1))