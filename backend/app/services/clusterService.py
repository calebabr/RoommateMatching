from sklearn.cluster import KMeans
import numpy as np
from app.services.matchScore import matchScore
from app.database import clusters_collection

class ClusterService:
    def __init__(self):
        self.scorer = matchScore()
        self.clusters = clusters_collection
        self.kmeans = None
        self.category_keys = list(self.scorer.categoryRange.keys())

    def user_to_vector(self, user: dict) -> list:
        return [user[cat][0] for cat in self.category_keys]

    def fit(self, users: list[dict]):
        n_clusters = max(2, len(users) // 100)
        vectors = np.array([self.user_to_vector(u) for u in users])
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        self.kmeans.fit(vectors)

    def assign_cluster(self, user: dict) -> int:
        vector = np.array([self.user_to_vector(user)])
        return int(self.kmeans.predict(vector)[0])

    def get_nearby_clusters(self, cluster_id: int, n=3) -> list[int]:
        centroid = self.kmeans.cluster_centers_[cluster_id]
        distances = []
        for i, c in enumerate(self.kmeans.cluster_centers_):
            if i != cluster_id:
                dist = np.linalg.norm(centroid - c)
                distances.append((i, dist))
        distances.sort(key=lambda x: x[1])
        return [cluster_id] + [d[0] for d in distances[:n]]

    async def store_user_cluster(self, user_id: int, cluster_id: int):
        await self.clusters.update_one(
            {"userId": user_id},
            {"$set": {"clusterId": cluster_id}},
            upsert=True
        )

    async def get_cluster_members(self, cluster_ids: list[int]) -> list[int]:
        cursor = self.clusters.find({"clusterId": {"$in": cluster_ids}})
        user_ids = []
        async for doc in cursor:
            user_ids.append(doc["userId"])
        return user_ids