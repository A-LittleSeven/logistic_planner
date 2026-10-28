import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans

from app.core.cluster.base_cluster import BaseCluster
from app.utils.logger import LogUtil

logger = LogUtil.get_logger(__name__)


class ConstrainedKmeansCluster(BaseCluster):
    def __init__(self, data: pd.DataFrame,
                 n_clusters,
                 lng_col='longitude',
                 lat_col='latitude',
                 freq_col='frequency',
                 max_iter=300,
                 tol=1e-4):
        super().__init__()
        self.data = data
        self.n_clusters = n_clusters
        self.lng_col = lng_col
        self.lat_col = lat_col
        self.freq_col = freq_col
        self.max_iter = max_iter
        self.tol = tol
        self.cluster_center = None
        self.delivery_freq = None

    def _get_min_cluster_size(self, cluster_delivery_freq):
        """根据配送频率与总体样本规模自适应确定最小聚类规模"""
        total_samples = len(self.data) if hasattr(self, 'data') and self.data is not None else 100
        avg_cluster_size = max(1, total_samples // max(1, self.n_clusters))

        # 基础规模取平均簇规模的 40%，且不超过 13
        base_min = max(1, min(13, int(avg_cluster_size * 0.4)))

        if len(cluster_delivery_freq) > 0:
            max_freq = np.max(cluster_delivery_freq)
            min_size = min(int(avg_cluster_size * 0.8), max(base_min, int(max_freq * 2)))
        else:
            min_size = base_min
        return max(1, min_size)

    def _init_centers(self, X):
        """改进的初始化：考虑空间分布和约束"""
        kmeans = KMeans(n_clusters=self.n_clusters, n_init=10, random_state=42)
        kmeans.fit(X)
        centers = kmeans.cluster_centers_
        return centers

    def getClusterCenter(self):
        """返回聚类中心 DataFrame，包含 center_lgt、center_lat、cluster_id"""
        df_center = pd.DataFrame(self.cluster_centers_, columns=["center_lgt", "center_lat"])
        df_center["cluster_id"] = range(len(df_center))
        return df_center

    def _assign_with_strong_constraints(self, X, centers, delivery_freq):
        """带强约束的分配步骤"""
        n_samples = X.shape[0]
        distances = cdist(X, centers, metric='euclidean')
        labels = np.argmin(distances, axis=1)
        labels = self._enforce_strong_constraints(X, labels, delivery_freq, distances)
        return labels

    def _enforce_strong_constraints(self, X, labels, delivery_freq, distances):
        """强制执行强约束的算法"""
        max_iterations = 1000

        for iteration in range(max_iterations):
            violations = self._check_all_violations(labels, delivery_freq)
            if not violations:
                break

            under_violations = [v for v in violations if v[2] == 'under']
            for cluster_id, violation_amount, _ in under_violations:
                self._add_points_to_cluster_strong(X, labels, cluster_id, violation_amount, distances, delivery_freq)

            violations = self._check_all_violations(labels, delivery_freq)
            if not violations:
                break

            modulo_violations = [v for v in violations if v[2] == 'modulo']
            for cluster_id, violation_amount, _ in modulo_violations:
                self._adjust_cluster_size_strong(X, labels, cluster_id, violation_amount, distances, delivery_freq)

        return labels

    def _check_all_violations(self, labels, delivery_freq):
        """全面检查所有约束违反情况"""
        violations = []

        for cluster_id in range(self.n_clusters):
            cluster_indices = np.where(labels == cluster_id)[0]

            if len(cluster_indices) == 0:
                violations.append((cluster_id, self._get_min_cluster_size([]), 'empty'))
                continue

            cluster_freq = delivery_freq[cluster_indices]
            min_size = self._get_min_cluster_size(cluster_freq)

            current_size = len(cluster_indices)
            size_violation = min_size - current_size

            if size_violation > 0:
                violations.append((cluster_id, size_violation, 'under'))

        return violations

    def _add_points_to_cluster_strong(self, X, labels, target_cluster, n_points_needed, distances, delivery_freq):
        """强化版：添加点到满足最小规模约束"""
        other_cluster_points = np.where(labels != target_cluster)[0]
        if len(other_cluster_points) == 0:
            return

        target_distances = distances[other_cluster_points, target_cluster]
        nearest_indices = other_cluster_points[np.argsort(target_distances)]

        points_moved = 0
        for point_idx in nearest_indices:
            if points_moved >= n_points_needed:
                break

            original_cluster = labels[point_idx]
            original_cluster_indices = np.where(labels == original_cluster)[0]

            original_cluster_freq = delivery_freq[original_cluster_indices]
            original_min_size = self._get_min_cluster_size(original_cluster_freq)

            if len(original_cluster_indices) > original_min_size:
                new_original_size = len(original_cluster_indices) - 1
                if new_original_size >= original_min_size:
                    labels[point_idx] = target_cluster
                    points_moved += 1

    def _adjust_cluster_size_strong(self, X, labels, cluster_id, remainder, distances, delivery_freq):
        """强化版：调整聚类大小"""
        cluster_indices = np.where(labels == cluster_id)[0]
        current_size = len(cluster_indices)

        cluster_freq = delivery_freq[cluster_indices]
        required_size = self._get_min_cluster_size(cluster_freq)

        if current_size > required_size:
            excess_points = current_size - required_size
            cluster_distances = distances[cluster_indices, cluster_id]
            farthest_indices = cluster_indices[np.argsort(-cluster_distances)[:excess_points]]

            for point_idx in farthest_indices:
                best_cluster = self._find_best_cluster_for_point(X, labels, point_idx, distances, delivery_freq)
                if best_cluster is not None:
                    labels[point_idx] = best_cluster

    def _find_best_cluster_for_point(self, X, labels, point_idx, distances, delivery_freq):
        """为点找到最适合的聚类"""
        current_cluster = labels[point_idx]
        best_cluster = None
        min_distance = float('inf')

        for cluster_id in range(self.n_clusters):
            if cluster_id == current_cluster:
                continue

            cluster_indices = np.where(labels == cluster_id)[0]
            if len(cluster_indices) > 0:
                cluster_freq = delivery_freq[cluster_indices]
                min_required = self._get_min_cluster_size(cluster_freq)

                new_size = len(cluster_indices) + 1
                if new_size >= min_required:
                    distance = distances[point_idx, cluster_id]
                    if distance < min_distance:
                        min_distance = distance
                        best_cluster = cluster_id

        return best_cluster

    def _local_search_optimization(self, X, labels, delivery_freq, max_iterations=100):
        """启发式局部搜索优化类内距离（增量式评估版）

        原实现每试探一次迁移就全量重算 _calculate_total_distance，
        复杂度 O(max_iter · n² · k)，几百门店即分钟级并阻塞同步请求线程。
        本版维护每簇 count/sum/sumsq 统计量，利用
        SSE_c = Σ||x||² - ||Σx||²/n_c 的分解，单次迁移评估降为 O(1)，
        整体降为 O(max_iter · n · k)，可接受性判据与原实现一致
        （迁移后所有簇仍满足最小规模约束 且 总距离下降）。
        """
        n_samples = X.shape[0]
        k = self.n_clusters
        if n_samples == 0 or k <= 1:
            return labels

        rng = np.random
        freqs = np.asarray(delivery_freq, dtype=float)
        sq_norms = np.einsum('ij,ij->i', X, X)
        current_labels = labels.astype(int).copy()

        # ---- 簇统计量初始化 ----
        counts = np.bincount(current_labels, minlength=k).astype(float)
        sums = np.vstack([np.bincount(current_labels, weights=X[:, d], minlength=k)
                          for d in range(X.shape[1])]).T.astype(float)
        sumsq = np.bincount(current_labels, weights=sq_norms, minlength=k).astype(float)

        def _cluster_max_freq(lbls, c, exclude_idx=None):
            mask = lbls == c
            if exclude_idx is not None:
                mask[exclude_idx] = False
            m = freqs[mask]
            return m.max() if m.size else 0.0

        def _sse_of(c_cnt, c_sum, c_sumsq):
            """单簇 SSE（负数截 0 防浮点误差）"""
            if c_cnt <= 0:
                return 0.0
            return max(0.0, c_sumsq - float(np.dot(c_sum, c_sum)) / c_cnt)

        def _min_size_for(lbls, c, extra_freq=None, exclude_idx=None):
            """簇 c 的最小规模阈值（extra_freq 模拟加入新点、exclude_idx 模拟移出点后的最大频次）"""
            mf = _cluster_max_freq(lbls, c, exclude_idx=exclude_idx)
            if extra_freq is not None:
                mf = max(mf, extra_freq)
            return self._get_min_cluster_size([mf] if mf > 0 else [])

        for iteration in range(max_iterations):
            improved = False

            for point_idx in rng.permutation(n_samples):
                a = current_labels[point_idx]
                x = X[point_idx]
                xn = sq_norms[point_idx]
                f = freqs[point_idx]

                sse_a = _sse_of(counts[a], sums[a], sumsq[a])
                sse_b_orig = np.empty(k)
                for b in range(k):
                    sse_b_orig[b] = _sse_of(counts[b], sums[b], sumsq[b])

                best_b = -1
                best_gain = -1e-12  # 仅接受严格下降

                # 源簇校验与 b 无关，先做一次（移出后仍满足最小规模）
                if counts[a] - 1 >= _min_size_for(current_labels, a, exclude_idx=point_idx):
                    for b in range(k):
                        if b == a:
                            continue
                        # 目标簇加入新点后须满足最小规模（频次上限可能被抬高）
                        if counts[b] + 1 < _min_size_for(current_labels, b, extra_freq=f):
                            continue

                        # 增量 SSE：只重算受影响的两个簇
                        sse_a_new = _sse_of(counts[a] - 1, sums[a] - x, sumsq[a] - xn)
                        sse_b_new = _sse_of(counts[b] + 1, sums[b] + x, sumsq[b] + xn)
                        gain = (sse_a_new + sse_b_new) - (sse_a + sse_b_orig[b])
                        if gain < best_gain:
                            best_gain = gain
                            best_b = b

                if best_b >= 0:
                    # 应用迁移并更新统计量
                    counts[a] -= 1
                    sums[a] -= x
                    sumsq[a] -= xn
                    counts[best_b] += 1
                    sums[best_b] += x
                    sumsq[best_b] += xn
                    current_labels[point_idx] = best_b
                    improved = True

            if not improved:
                break

        return current_labels

    def fit(self, warehouse_lng=None, warehouse_lat=None):
        """主拟合函数"""
        X = np.asarray((self.data[self.lng_col].values, self.data[self.lat_col].values)).T
        delivery_freq = self.data[self.freq_col].values
        self.delivery_freq = delivery_freq
        centers = self._init_centers(X)
        for iteration in range(self.max_iter):
            labels = self._assign_with_strong_constraints(X, centers, delivery_freq)

            new_centers = np.zeros_like(centers)
            for j in range(self.n_clusters):
                cluster_points = X[labels == j]
                if len(cluster_points) > 0:
                    new_centers[j] = cluster_points.mean(axis=0)
                else:
                    new_centers[j] = centers[j]
            center_shift = np.sqrt(np.sum((new_centers - centers) ** 2, axis=1))
            if np.max(center_shift) < self.tol:
                break
            centers = new_centers

        self.cluster_centers_ = centers
        self.labels_ = labels

        logger.info("约束聚类收敛完成，开始启发式局部搜索优化...")
        optimized_labels = self._local_search_optimization(X, labels, delivery_freq)
        self.labels_ = optimized_labels

        # 局部搜索迁移了门店归属，须按优化后标签重算簇中心，
        # 否则输出的 center_lgt/center_lat 与簇内实际门店位置偏离
        new_centers = np.zeros_like(self.cluster_centers_)
        for j in range(self.n_clusters):
            cluster_points = X[self.labels_ == j]
            if len(cluster_points) > 0:
                new_centers[j] = cluster_points.mean(axis=0)
            else:
                new_centers[j] = self.cluster_centers_[j]  # 空簇保留旧中心
        self.cluster_centers_ = new_centers

        self.data = self.data.assign(cluster_id=self.labels_)
        self.cluster_center = self.getClusterCenter()
        # left join 保证标签缺失/异常时不静默丢门店行（与 district_extension_cluster 保持一致）
        self.data = pd.merge(self.data, self.cluster_center, on="cluster_id", how="left")

        if warehouse_lng is not None and warehouse_lat is not None:
            self.cdist_calc(warehouse_lng, warehouse_lat)

        return self
