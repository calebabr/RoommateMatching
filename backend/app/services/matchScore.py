import math

class matchScore:
    def __init__(self):
        self.categoryRange = {
            "sleepScheduleWeekdays": [24, 0.125], # 3 hours difference is a dealbreaker. Value should correspond to
                                                # the military time equivalent to the user's quiet hours
            "sleepScheduleWeekends": [24, 0.125],
            "cleanliness": [10, 0.2], # range of 0-10, 2 point difference is dealbreaker. 0 is messy, 10 is neat freak
            "noiseTolerance": [10, 0.2], # range of 0-10, 2 point difference is dealbreaker, 0 is quiet, 10 is very loud
            "guests": [10, 1.0], # range of 0-10. no dealbreaker range. dealbreaker is defined if one person doesn't want people over. 0 means people will not be over a lot, 10 means people will always be visiting
        }

    def dealBreak(self, category, user1, user2) -> float:
        """
        Checks if a preference difference between two users is a dealbreaker.

        Parameters:
            category (str): The preference category to check (e.g., 'cleanliness', 'noiseTolerance').
            user1 (dict): First user's preference data.
            user2 (dict): Second user's preference data.

        Returns:
            float: 0.0 if the difference is a dealbreaker, 1.0 otherwise.
        """
        if (user1[category][1] or user2[category][1]) and math.fabs(user1[category][0] - user2[category][0]) > self.categoryRange[category][0] * self.categoryRange[category][1]:
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

    def matchScore(self, user1, user2) -> float:
        """
        Calculates the overall match score from user1's perspective to user2.

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
        for c in self.categoryRange.keys():
            weightedSum += self.preferenceScore(c, user1[c][0], user2[c][0])
        return weightedSum / len(self.categoryRange.keys())

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