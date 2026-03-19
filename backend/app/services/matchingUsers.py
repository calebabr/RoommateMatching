import networkx as nx
from app.services.matchScore import matchScore

class matchingUsers:
    def __init__(self):
        self.scorer = matchScore()

    def buildCompatibilityGraph(self, users):
        """
        Builds a weighted graph where nodes are users and edges represent compatibility.

        Parameters:
            users (list[dict]): List of user profiles with preference information.

        Returns:
            networkx.Graph: Graph where node IDs are user IDs and edge weights are compatibility scores.

        Notes:
            Only positive compatibility scores result in edges being created.
        """
        G = nx.Graph()

        for u in users:
            G.add_node(u["id"])

        for i in range(len(users)):
            for j in range(i + 1, len(users)):
                score = self.scorer.compatibilityScore(users[i], users[j])
                if score > 0:
                    G.add_edge(users[i]["id"], users[j]["id"], weight=score)

        return G

    def find_matches(self, users: list[dict]) -> dict:
        """
        Finds optimal pairings of users based on compatibility scores using maximum weight matching.

        Parameters:
            users (list[dict]): List of user profiles to match.

        Returns:
            dict: Contains two keys:
                - 'matches': List of match pairs with user IDs and compatibility scores, sorted descending.
                - 'unmatched_users': List of user IDs that could not be paired.

        Notes:
            Uses graph-based maximum weight matching algorithm to ensure globally optimal pairs.
        """
        G = self.buildCompatibilityGraph(users)
        matching = nx.max_weight_matching(G, maxcardinality=True)

        matched_ids = set()
        results = []
        for u1_id, u2_id in matching:
            score = G[u1_id][u2_id]["weight"]
            results.append({
                "user1_id": u1_id,
                "user2_id": u2_id,
                "compatibilityScore": score
            })
            matched_ids.add(u1_id)
            matched_ids.add(u2_id)

        results.sort(key=lambda x: x["compatibilityScore"], reverse=True)

        all_ids = {u["id"] for u in users}
        unmatched = list(all_ids - matched_ids)

        return {
            "matches": results,
            "unmatched_users": unmatched
        }