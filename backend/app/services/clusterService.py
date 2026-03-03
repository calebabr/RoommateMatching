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
        """
        Converts a user profile to a numerical vector based on preference categories.

        Parameters:
            user (dict): User profile object with preference categories.

        Returns:
            list: Vector of preference values in the order of category_keys.
        """
        return [user[cat][0] for cat in self.category_keys]

    def fit(self, users: list[dict]):
        """
        Trains the K-means clustering model on user preference vectors.

        Parameters:
            users (list[dict]): List of user profiles to cluster.

        Returns:
            None (trains internal kmeans model)

        Notes:
            Number of clusters is determined as max(2, len(users) // 100).
            Uses random_state=42 for reproducibility.
        """
        n_clusters = max(2, len(users) // 100)
        vectors = np.array([self.user_to_vector(u) for u in users])
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        self.kmeans.fit(vectors)

    def assign_cluster(self, user: dict) -> int:
        """
        Assigns a user to their nearest cluster based on trained K-means model.

        Parameters:
            user (dict): User profile to assign to a cluster.

        Returns:
            int: The cluster ID (0-indexed) assigned to the user.
        """
        vector = np.array([self.user_to_vector(user)])
        return int(self.kmeans.predict(vector)[0])

    def get_nearby_clusters(self, cluster_id: int, n=3) -> list[int]:
        """
        Finds the closest clusters to a given cluster based on centroid distances.

        Parameters:
            cluster_id (int): The reference cluster ID.
            n (int): Number of nearby clusters to return (default 3).

        Returns:
            list[int]: List containing the query cluster_id plus up to n nearest clusters.
        """
        centroid = self.kmeans.cluster_centers_[cluster_id]
        distances = []
        for i, c in enumerate(self.kmeans.cluster_centers_):
            if i != cluster_id:
                dist = np.linalg.norm(centroid - c)
                distances.append((i, dist))
        distances.sort(key=lambda x: x[1])
        return [cluster_id] + [d[0] for d in distances[:n]]

    async def store_user_cluster(self, user_id: int, cluster_id: int):
        """
        Stores the cluster assignment for a user in the database.

        Parameters:
            user_id (int): The user ID to store cluster assignment for.
            cluster_id (int): The cluster ID to assign.

        Returns:
            None

        Notes:
            Uses upsert=True to create or update the cluster assignment.
        """
        await self.clusters.update_one(
            {"userId": user_id},
            {"$set": {"clusterId": cluster_id}},
            upsert=True
        )

    async def get_cluster_members(self, cluster_ids: list[int]) -> list[int]:
        """
        Retrieves all user IDs belonging to specified clusters.

        Parameters:
            cluster_ids (list[int]): List of cluster IDs to retrieve members from.

        Returns:
            list[int]: List of user IDs in the specified clusters.
        """
        cursor = self.clusters.find({"clusterId": {"$in": cluster_ids}})
        user_ids = []
        async for doc in cursor:
            user_ids.append(doc["userId"])
        return user_ids