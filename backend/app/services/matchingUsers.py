import networkx as nx
from app.services.matchScore import matchScore

class matchingUsers:
    def __init__(self):
        self.scorer = matchScore()

    def buildCompatibilityGraph(self, users):
        G = nx.Graph()

        for u in users:
            G.add_node(u["id"]) # Create nodes for each user

        for i in range(len(users)): # Assign weights to edges based on compatibility scores
            for j in range(i + 1, len(users)):
                score = self.scorer.compatibilityScore(users[i], users[j])
                if score > 0:
                    G.add_edge(users[i]["id"], users[j]["id"], weight=score)

        return G

    def find_matches(self, users: list[dict]) -> dict:
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