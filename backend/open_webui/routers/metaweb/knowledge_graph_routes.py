"""
MetaWeb Knowledge Graph API Routes
知识图谱API路由 - 增强版 with Learning Path Recommendation
"""
import logging
import json
from typing import List, Dict, Optional, Set
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import text

from open_webui.internal.db import Session, get_db
from open_webui.utils.auth import get_current_user
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Response Models
# ============================================

class KnowledgePoint(BaseModel):
    id: str
    knowledge_point: str
    subject: str
    category: Optional[str]
    prerequisites: List[str]
    related_points: List[str]
    difficulty_level: int
    estimated_hours: float
    description: Optional[str]
    created_at: str
    updated_at: str


class KnowledgeGraphNode(BaseModel):
    """知识图谱节点 - 用于前端可视化"""
    id: str
    label: str
    subject: str
    category: Optional[str]
    difficulty_level: int
    mastery_level: Optional[float] = None  # 学生掌握度


class KnowledgeGraphEdge(BaseModel):
    """知识图谱边 - 表示知识点之间的关系"""
    from_node: str
    to_node: str
    relation_type: str  # 'prerequisite' or 'related'


class LearningPath(BaseModel):
    id: str
    student_id: str
    target_knowledge_point: str
    recommended_path: List[str]
    current_step: int
    total_steps: int
    reason: Optional[str]
    status: str
    created_at: str
    updated_at: str


class LearningPathRecommendation(BaseModel):
    """学习路径推荐响应 - 增强版"""
    path: List[str]  # 知识点名称列表(按学习顺序)
    estimated_hours: float  # 预计总学时
    difficulty_avg: float  # 平均难度
    details: List[Dict]  # 每个知识点的详细信息


# ============================================
# Helper Functions
# ============================================

def topological_sort_with_priority(
    unmastered_points: Dict,
    mastered_points: Set[str],
    all_points: Dict
) -> List[str]:
    """
    拓扑排序 + 优先级调整

    优先级规则:
    1. 前置知识点全部已掌握的优先
    2. 难度较低的优先
    3. 没有前置要求的优先(基础知识点)
    """
    # 构建图
    graph = defaultdict(list)  # name -> [依赖它的节点]
    in_degree = defaultdict(int)  # name -> 入度(有多少前置)

    # 初始化所有未掌握节点的入度
    for name in unmastered_points:
        in_degree[name] = 0

    # 计算入度
    for name, info in unmastered_points.items():
        prerequisites = info["prerequisites"]

        for prereq in prerequisites:
            if prereq in unmastered_points:
                # 前置也未掌握,建立依赖关系
                graph[prereq].append(name)
                in_degree[name] += 1
            # 如果前置已掌握,不计入入度

    # 找出所有入度为0的节点(可以立即学习的)
    queue = []
    for name in unmastered_points:
        if in_degree[name] == 0:
            # 按难度排序,优先学简单的
            queue.append((unmastered_points[name]["difficulty"], name))

    queue.sort()  # 按难度排序
    queue = deque([name for _, name in queue])

    result = []

    while queue:
        # 取出一个节点
        current = queue.popleft()
        result.append(current)

        # 处理依赖它的节点
        next_nodes = []
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                # 该节点的所有前置都已处理,可以学习了
                next_nodes.append((
                    unmastered_points[neighbor]["difficulty"],
                    neighbor
                ))

        # 按难度排序后加入队列
        next_nodes.sort()
        for _, name in next_nodes:
            queue.append(name)

    # 处理环路(如果有)
    if len(result) < len(unmastered_points):
        # 有环,把剩余的节点按难度排序后加入
        remaining = [
            (unmastered_points[name]["difficulty"], name)
            for name in unmastered_points
            if name not in result
        ]
        remaining.sort()
        result.extend([name for _, name in remaining])

    return result


# ============================================
# API Endpoints
# ============================================

@router.get("/knowledge-graph")
async def get_knowledge_graph(
    subject: Optional[str] = None,
    user: Users = Depends(get_current_user)
):
    """
    获取知识图谱完整数据

    返回节点和边的数据结构,供前端可视化使用
    """
    session = next(get_db())

    try:
        # 构建查询
        query = """
            SELECT
                id, knowledge_point, subject, category,
                prerequisites, related_points,
                difficulty_level, estimated_hours, description
            FROM knowledge_graph
        """
        params = {}

        if subject:
            query += " WHERE subject = :subject"
            params['subject'] = subject

        query += " ORDER BY difficulty_level, knowledge_point"

        result = session.execute(text(query), params)

        nodes = []
        edges = []

        # 如果是学生,获取其掌握度数据
        mastery_data = {}
        if user.role == 'student':
            mastery_query = text("""
                SELECT knowledge_point, mastery_level
                FROM student_knowledge_profile
                WHERE student_id = :student_id
            """)
            mastery_result = session.execute(mastery_query, {'student_id': user.id})
            mastery_data = {row[0]: row[1] for row in mastery_result.fetchall()}

        # 处理查询结果
        for row in result.fetchall():
            kp_id = row[0]
            kp_name = row[1]

            # 创建节点
            node = KnowledgeGraphNode(
                id=kp_id,
                label=kp_name,
                subject=row[2],
                category=row[3],
                difficulty_level=row[6],
                mastery_level=mastery_data.get(kp_name)
            )
            nodes.append(node)

            # 解析前置知识点,创建边
            prerequisites = json.loads(row[4]) if row[4] else []
            for prereq in prerequisites:
                edges.append(KnowledgeGraphEdge(
                    from_node=prereq,
                    to_node=kp_name,
                    relation_type='prerequisite'
                ))

            # 解析相关知识点,创建边
            related = json.loads(row[5]) if row[5] else []
            for rel in related:
                edges.append(KnowledgeGraphEdge(
                    from_node=kp_name,
                    to_node=rel,
                    relation_type='related'
                ))

        return {
            'nodes': [n.dict() for n in nodes],
            'edges': [e.dict() for e in edges]
        }

    except Exception as e:
        log.error(f"Error fetching knowledge graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-points")
async def get_knowledge_points(
    subject: Optional[str] = None,
    category: Optional[str] = None,
    difficulty_min: Optional[int] = None,
    difficulty_max: Optional[int] = None,
    user: Users = Depends(get_current_user)
):
    """
    获取知识点列表

    支持按科目、分类、难度筛选
    """
    session = next(get_db())

    try:
        query = """
            SELECT
                id, knowledge_point, subject, category,
                prerequisites, related_points,
                difficulty_level, estimated_hours, description,
                created_at, updated_at
            FROM knowledge_graph
            WHERE 1=1
        """
        params = {}

        if subject:
            query += " AND subject = :subject"
            params['subject'] = subject

        if category:
            query += " AND category = :category"
            params['category'] = category

        if difficulty_min is not None:
            query += " AND difficulty_level >= :diff_min"
            params['diff_min'] = difficulty_min

        if difficulty_max is not None:
            query += " AND difficulty_level <= :diff_max"
            params['diff_max'] = difficulty_max

        query += " ORDER BY subject, difficulty_level, knowledge_point"

        result = session.execute(text(query), params)

        knowledge_points = []
        for row in result.fetchall():
            kp = KnowledgePoint(
                id=row[0],
                knowledge_point=row[1],
                subject=row[2],
                category=row[3],
                prerequisites=json.loads(row[4]) if row[4] else [],
                related_points=json.loads(row[5]) if row[5] else [],
                difficulty_level=row[6],
                estimated_hours=row[7],
                description=row[8],
                created_at=row[9],
                updated_at=row[10]
            )
            knowledge_points.append(kp)

        return knowledge_points

    except Exception as e:
        log.error(f"Error fetching knowledge points: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-points/{knowledge_point_id}")
async def get_knowledge_point(
    knowledge_point_id: str,
    user: Users = Depends(get_current_user)
):
    """
    获取单个知识点详情
    """
    session = next(get_db())

    try:
        query = text("""
            SELECT
                id, knowledge_point, subject, category,
                prerequisites, related_points,
                difficulty_level, estimated_hours, description,
                created_at, updated_at
            FROM knowledge_graph
            WHERE id = :id
        """)

        result = session.execute(query, {'id': knowledge_point_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Knowledge point not found")

        kp = KnowledgePoint(
            id=result[0],
            knowledge_point=result[1],
            subject=result[2],
            category=result[3],
            prerequisites=json.loads(result[4]) if result[4] else [],
            related_points=json.loads(result[5]) if result[5] else [],
            difficulty_level=result[6],
            estimated_hours=result[7],
            description=result[8],
            created_at=result[9],
            updated_at=result[10]
        )

        return kp

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching knowledge point: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning-path/recommend", response_model=LearningPathRecommendation)
async def recommend_learning_path(
    subject: str = "数学",
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    推荐学习路径 - 增强版

    算法逻辑:
    1. 获取该科目所有知识点
    2. 获取学生掌握度数据(如果是学生)
    3. 筛选未掌握的知识点 (mastery_level < 0.8 or null)
    4. 根据前置关系进行拓扑排序
    5. 优先推荐:
       - 前置知识点已掌握
       - 难度递增
       - 重要性高(被引用多的知识点)
    """
    try:
        log.info(f"用户 {user.id} 请求 {subject} 学习路径推荐")

        # 1. 获取所有知识点
        query = text("""
            SELECT
                id, knowledge_point, subject, category,
                prerequisites, difficulty_level, estimated_hours,
                description
            FROM knowledge_graph
            WHERE subject = :subject
            ORDER BY difficulty_level ASC
        """)

        result = db.execute(query, {"subject": subject})
        all_points = {}

        for row in result.fetchall():
            point_id = row[0]
            all_points[row[1]] = {
                "id": point_id,
                "name": row[1],
                "subject": row[2],
                "category": row[3],
                "prerequisites": json.loads(row[4]) if row[4] else [],
                "difficulty": row[5],
                "hours": row[6],
                "description": row[7]
            }

        # 2. 获取学生掌握度(如果是学生)
        mastered_points = set()
        if user.role == "student" or user.role == "user":  # user也算学生
            mastery_query = text("""
                SELECT knowledge_point, mastery_level
                FROM student_knowledge_profile
                WHERE student_id = :student_id AND subject = :subject
            """)

            mastery_result = db.execute(mastery_query, {
                "student_id": user.id,
                "subject": subject
            })

            for row in mastery_result.fetchall():
                if row[1] >= 0.8:  # 掌握度 >= 80% 算已掌握
                    mastered_points.add(row[0])

        log.info(f"学生已掌握 {len(mastered_points)} 个知识点")

        # 3. 筛选未掌握的知识点
        unmastered_points = {
            name: info for name, info in all_points.items()
            if name not in mastered_points
        }

        if not unmastered_points:
            # 全部掌握,返回空路径
            return LearningPathRecommendation(
                path=[],
                estimated_hours=0,
                difficulty_avg=0,
                details=[]
            )

        # 4. 拓扑排序 + 优先级调整
        recommended_path = topological_sort_with_priority(
            unmastered_points,
            mastered_points,
            all_points
        )

        # 5. 计算统计信息
        total_hours = sum(all_points[name]["hours"] for name in recommended_path)
        avg_difficulty = sum(all_points[name]["difficulty"] for name in recommended_path) / len(recommended_path)

        # 6. 构建详细信息
        details = []
        for idx, name in enumerate(recommended_path, 1):
            point = all_points[name]
            details.append({
                "order": idx,
                "name": name,
                "difficulty": point["difficulty"],
                "hours": point["hours"],
                "prerequisites": point["prerequisites"],
                "mastered": name in mastered_points
            })

        log.info(f"推荐路径: {recommended_path}")

        return LearningPathRecommendation(
            path=recommended_path,
            estimated_hours=round(total_hours, 1),
            difficulty_avg=round(avg_difficulty, 2),
            details=details
        )

    except Exception as e:
        log.error(f"推荐学习路径失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


@router.get("/learning-path/{student_id}")
async def get_learning_paths(
    student_id: str,
    status: Optional[str] = None,
    user: Users = Depends(get_current_user)
):
    """
    获取学生的学习路径列表
    """
    # 权限检查
    if user.role not in ['admin', 'leader', 'teacher']:
        if user.id != student_id:
            raise HTTPException(status_code=403, detail="Permission denied")

    session = next(get_db())

    try:
        query = """
            SELECT
                id, student_id, target_knowledge_point,
                recommended_path, current_step, total_steps,
                reason, status, created_at, updated_at
            FROM learning_paths
            WHERE student_id = :student_id
        """
        params = {'student_id': student_id}

        if status:
            query += " AND status = :status"
            params['status'] = status

        query += " ORDER BY created_at DESC"

        result = session.execute(text(query), params)

        paths = []
        for row in result.fetchall():
            path = LearningPath(
                id=row[0],
                student_id=row[1],
                target_knowledge_point=row[2],
                recommended_path=json.loads(row[3]),
                current_step=row[4],
                total_steps=row[5],
                reason=row[6],
                status=row[7],
                created_at=row[8],
                updated_at=row[9]
            )
            paths.append(path)

        return paths

    except Exception as e:
        log.error(f"Error fetching learning paths: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subjects")
async def get_subjects(
    user: Users = Depends(get_current_user)
):
    """
    获取所有科目列表
    """
    session = next(get_db())

    try:
        query = text("""
            SELECT DISTINCT subject
            FROM knowledge_graph
            ORDER BY subject
        """)

        result = session.execute(query)
        subjects = [row[0] for row in result.fetchall()]

        return subjects

    except Exception as e:
        log.error(f"Error fetching subjects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_knowledge_graph_statistics(
    user: Users = Depends(get_current_user)
):
    """
    获取知识图谱统计数据
    """
    session = next(get_db())

    try:
        # 按科目统计
        subject_stats = text("""
            SELECT
                subject,
                COUNT(*) as total,
                AVG(difficulty_level) as avg_difficulty,
                SUM(estimated_hours) as total_hours
            FROM knowledge_graph
            GROUP BY subject
            ORDER BY total DESC
        """)

        result = session.execute(subject_stats)

        stats = []
        for row in result.fetchall():
            stats.append({
                'subject': row[0],
                'total_knowledge_points': row[1],
                'average_difficulty': round(row[2], 2),
                'total_estimated_hours': round(row[3], 1)
            })

        # 整体统计
        overall_stats = text("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT subject) as total_subjects,
                AVG(difficulty_level) as avg_difficulty,
                MIN(difficulty_level) as min_difficulty,
                MAX(difficulty_level) as max_difficulty
            FROM knowledge_graph
        """)

        overall = session.execute(overall_stats).fetchone()

        return {
            'overall': {
                'total_knowledge_points': overall[0],
                'total_subjects': overall[1],
                'average_difficulty': round(overall[2], 2),
                'difficulty_range': [overall[3], overall[4]]
            },
            'by_subject': stats
        }

    except Exception as e:
        log.error(f"Error fetching statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
