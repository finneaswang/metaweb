"""
MetaWeb AI Secretary Module
负责每日自动分析学生数据,更新知识图谱,生成学习报告
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from open_webui.internal.db import Session

log = logging.getLogger(__name__)


class AISecretary:
    """AI秘书核心类 - 负责自动化学生数据分析"""

    def __init__(self, db_session):
        self.session = db_session
        self.scheduler = BackgroundScheduler()

    def start(self):
        """启动定时任务"""
        # 每晚23:00执行分析
        self.scheduler.add_job(
            func=self.nightly_analysis,
            trigger=CronTrigger(hour=23, minute=0),
            id='nightly_student_analysis',
            name='每日学生数据分析',
            replace_existing=True
        )
        self.scheduler.start()
        log.info("AI Secretary scheduler started - nightly analysis at 23:00")

    def stop(self):
        """停止定时任务"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            log.info("AI Secretary scheduler stopped")

    def nightly_analysis(self):
        """每日分析主入口"""
        log.info("Starting nightly student analysis...")

        try:
            # 1. 获取今日有新批改的学生
            students = self._get_students_with_new_grades()
            log.info(f"Found {len(students)} students with new grades today")

            # 2. 为每个学生创建分析任务
            for student in students:
                self._create_analysis_task(
                    student_id=student['id'],
                    task_type='daily_analysis'
                )

            # 3. 处理待处理的任务队列
            self._process_pending_tasks()

            # 4. 生成周报(每周日额外执行)
            if datetime.now().weekday() == 6:  # Sunday
                self._generate_weekly_reports()

            log.info("Nightly analysis completed successfully")

        except Exception as e:
            log.error(f"Error in nightly analysis: {str(e)}", exc_info=True)

    def _get_students_with_new_grades(self) -> List[Dict]:
        """获取今日有新批改作业的学生列表"""
        query = text("""
            SELECT DISTINCT
                u.id,
                u.name,
                u.email
            FROM user u
            JOIN submissions s ON s.student_id = u.id
            WHERE u.role = 'student'
              AND s.status IN ('graded', 'returned')
              AND date(s.updated_at) = date('now')
        """)

        result = self.session.execute(query)
        return [{"id": row[0], "name": row[1], "email": row[2]} for row in result]

    def _create_analysis_task(self, student_id: str, task_type: str):
        """创建AI分析任务"""
        query = text("""
            INSERT INTO ai_task_queue (
                task_type,
                task_data,
                priority,
                status,
                scheduled_at
            ) VALUES (
                :task_type,
                :task_data,
                :priority,
                'pending',
                datetime('now')
            )
        """)

        import json
        task_data = json.dumps({
            'student_id': student_id,
            'analysis_date': datetime.now().isoformat()
        })

        self.session.execute(query, {
            'task_type': task_type,
            'task_data': task_data,
            'priority': 5
        })
        self.session.commit()
        log.info(f"Created analysis task for student {student_id}")

    def _process_pending_tasks(self):
        """处理待处理的任务队列"""
        # 获取待处理任务
        query = text("""
            SELECT id, task_type, task_data
            FROM ai_task_queue
            WHERE status = 'pending'
              AND retry_count < max_retries
            ORDER BY priority DESC, scheduled_at ASC
            LIMIT 10
        """)

        result = self.session.execute(query)
        tasks = result.fetchall()

        for task_id, task_type, task_data in tasks:
            try:
                # 标记为处理中
                self.session.execute(
                    text("UPDATE ai_task_queue SET status = 'processing', started_at = datetime('now') WHERE id = :id"),
                    {'id': task_id}
                )
                self.session.commit()

                # 执行任务
                import json
                data = json.loads(task_data)

                if task_type == 'daily_analysis':
                    result = self._analyze_student_data(data['student_id'])
                else:
                    result = {'status': 'unknown_task_type'}

                # 标记为完成
                self.session.execute(
                    text("""
                        UPDATE ai_task_queue
                        SET status = 'completed',
                            completed_at = datetime('now'),
                            result = :result
                        WHERE id = :id
                    """),
                    {'id': task_id, 'result': json.dumps(result)}
                )
                self.session.commit()
                log.info(f"Task {task_id} completed successfully")

            except Exception as e:
                log.error(f"Error processing task {task_id}: {str(e)}")
                # 标记为失败并增加重试次数
                self.session.execute(
                    text("""
                        UPDATE ai_task_queue
                        SET status = 'failed',
                            error_message = :error,
                            retry_count = retry_count + 1
                        WHERE id = :id
                    """),
                    {'id': task_id, 'error': str(e)}
                )
                self.session.commit()

    def _analyze_student_data(self, student_id: str) -> Dict:
        """分析学生数据 - 核心AI分析逻辑"""
        log.info(f"Analyzing data for student {student_id}")

        # 1. 获取学生最近的提交记录
        submissions = self._get_recent_submissions(student_id, days=7)

        if not submissions:
            return {'status': 'no_data', 'message': 'No recent submissions'}

        # 2. 更新知识图谱
        knowledge_updates = self._update_knowledge_profile(student_id, submissions)

        # 3. 生成每日总结
        daily_summary = self._generate_daily_summary(student_id, submissions)

        return {
            'status': 'success',
            'student_id': student_id,
            'submissions_analyzed': len(submissions),
            'knowledge_updates': knowledge_updates,
            'daily_summary': daily_summary
        }

    def _get_recent_submissions(self, student_id: str, days: int = 7) -> List[Dict]:
        """获取学生最近的提交记录"""
        query = text("""
            SELECT
                s.id,
                s.assignment_id,
                a.subject,
                s.teacher_score,
                s.ai_score,
                s.teacher_feedback,
                s.ai_feedback,
                s.mistakes_analysis,
                s.submitted_at,
                s.updated_at
            FROM submissions s
            JOIN assignments a ON a.id = s.assignment_id
            WHERE s.student_id = :student_id
              AND s.status IN ('graded', 'returned')
              AND date(s.updated_at) >= date('now', '-' || :days || ' days')
            ORDER BY s.updated_at DESC
        """)

        result = self.session.execute(query, {'student_id': student_id, 'days': days})

        submissions = []
        for row in result:
            submissions.append({
                'id': row[0],
                'assignment_id': row[1],
                'subject': row[2],
                'teacher_score': row[3],
                'ai_score': row[4],
                'teacher_feedback': row[5],
                'ai_feedback': row[6],
                'mistakes_analysis': row[7],
                'submitted_at': row[8],
                'updated_at': row[9]
            })

        return submissions

    def _update_knowledge_profile(self, student_id: str, submissions: List[Dict]) -> Dict:
        """更新学生知识图谱"""
        import json
        knowledge_updates = {}

        for submission in submissions:
            subject = submission['subject']

            # 解析错题分析,提取知识点
            if submission['mistakes_analysis']:
                try:
                    mistakes = json.loads(submission['mistakes_analysis'])

                    for mistake in mistakes.get('mistakes', []):
                        knowledge_point = mistake.get('knowledge_point', '未分类')
                        is_correct = mistake.get('is_correct', False)

                        # 更新或创建知识点记录
                        self._update_knowledge_point(
                            student_id=student_id,
                            subject=subject,
                            knowledge_point=knowledge_point,
                            is_correct=is_correct
                        )

                        if knowledge_point not in knowledge_updates:
                            knowledge_updates[knowledge_point] = {'attempts': 0, 'correct': 0}

                        knowledge_updates[knowledge_point]['attempts'] += 1
                        if is_correct:
                            knowledge_updates[knowledge_point]['correct'] += 1

                except json.JSONDecodeError:
                    log.warning(f"Failed to parse mistakes_analysis for submission {submission['id']}")

        return knowledge_updates

    def _update_knowledge_point(self, student_id: str, subject: str,
                                knowledge_point: str, is_correct: bool):
        """更新单个知识点的掌握度"""
        # 检查是否存在
        check_query = text("""
            SELECT id, total_attempts, correct_attempts, mastery_level
            FROM student_knowledge_profile
            WHERE student_id = :student_id
              AND subject = :subject
              AND knowledge_point = :knowledge_point
        """)

        result = self.session.execute(check_query, {
            'student_id': student_id,
            'subject': subject,
            'knowledge_point': knowledge_point
        }).fetchone()

        if result:
            # 更新现有记录
            total = result[1] + 1
            correct = result[2] + (1 if is_correct else 0)
            mastery = round(correct / total, 2)

            update_query = text("""
                UPDATE student_knowledge_profile
                SET total_attempts = :total,
                    correct_attempts = :correct,
                    mastery_level = :mastery,
                    last_practiced = datetime('now'),
                    updated_at = datetime('now')
                WHERE id = :id
            """)

            self.session.execute(update_query, {
                'id': result[0],
                'total': total,
                'correct': correct,
                'mastery': mastery
            })
        else:
            # 创建新记录
            insert_query = text("""
                INSERT INTO student_knowledge_profile (
                    student_id,
                    subject,
                    knowledge_point,
                    total_attempts,
                    correct_attempts,
                    mastery_level,
                    first_encountered,
                    last_practiced
                ) VALUES (
                    :student_id,
                    :subject,
                    :knowledge_point,
                    1,
                    :correct,
                    :mastery,
                    datetime('now'),
                    datetime('now')
                )
            """)

            self.session.execute(insert_query, {
                'student_id': student_id,
                'subject': subject,
                'knowledge_point': knowledge_point,
                'correct': 1 if is_correct else 0,
                'mastery': 1.0 if is_correct else 0.0
            })

        self.session.commit()

    def _generate_daily_summary(self, student_id: str, submissions: List[Dict]) -> str:
        """生成每日学习总结"""
        # 这里简化处理,实际应该调用AI生成个性化总结
        total_submissions = len(submissions)
        subjects = set(s['subject'] for s in submissions)

        avg_score = sum(s['teacher_score'] or s['ai_score'] or 0 for s in submissions) / total_submissions if total_submissions > 0 else 0

        summary = f"今日完成{total_submissions}项作业,涉及{len(subjects)}个科目,平均得分{avg_score:.1f}分"

        return summary

    def _generate_weekly_reports(self):
        """生成周报"""
        log.info("Generating weekly reports for all students...")

        # 获取所有学生
        query = text("SELECT id, name FROM user WHERE role = 'student'")
        result = self.session.execute(query)
        students = result.fetchall()

        for student_id, student_name in students:
            try:
                self._generate_student_weekly_report(student_id)
            except Exception as e:
                log.error(f"Error generating weekly report for {student_name}: {str(e)}")

    def _generate_student_weekly_report(self, student_id: str):
        """为单个学生生成周报"""
        import json

        # 获取本周数据
        submissions = self._get_recent_submissions(student_id, days=7)

        if not submissions:
            log.info(f"No submissions this week for student {student_id}")
            return

        # 统计数据
        total = len(submissions)
        subjects = {}

        for s in submissions:
            subject = s['subject']
            score = s['teacher_score'] or s['ai_score'] or 0

            if subject not in subjects:
                subjects[subject] = {'count': 0, 'total_score': 0, 'scores': []}

            subjects[subject]['count'] += 1
            subjects[subject]['total_score'] += score
            subjects[subject]['scores'].append(score)

        # 构建周报
        strengths = []
        weaknesses = []

        for subject, data in subjects.items():
            avg = data['total_score'] / data['count']
            if avg >= 85:
                strengths.append(f"{subject}(平均{avg:.1f}分)")
            elif avg < 70:
                weaknesses.append(f"{subject}(平均{avg:.1f}分)")

        summary = f"本周完成{total}项作业,涉及{len(subjects)}个科目"

        # 保存周报
        insert_query = text("""
            INSERT INTO learning_reports (
                student_id,
                report_type,
                period_start,
                period_end,
                summary,
                strengths,
                weaknesses,
                statistics,
                generated_by
            ) VALUES (
                :student_id,
                'weekly',
                date('now', '-7 days'),
                date('now'),
                :summary,
                :strengths,
                :weaknesses,
                :statistics,
                'ai'
            )
        """)

        self.session.execute(insert_query, {
            'student_id': student_id,
            'summary': summary,
            'strengths': json.dumps(strengths, ensure_ascii=False),
            'weaknesses': json.dumps(weaknesses, ensure_ascii=False),
            'statistics': json.dumps(subjects, ensure_ascii=False)
        })
        self.session.commit()

        log.info(f"Weekly report generated for student {student_id}")


# 全局实例
_ai_secretary_instance: Optional[AISecretary] = None


def get_ai_secretary(session=None) -> AISecretary:
    """获取AI秘书单例"""
    global _ai_secretary_instance

    if _ai_secretary_instance is None:
        if session is None:
            session = Session()
        _ai_secretary_instance = AISecretary(session)

    return _ai_secretary_instance


def start_ai_secretary():
    """启动AI秘书服务"""
    secretary = get_ai_secretary()
    secretary.start()
    log.info("AI Secretary service started")


def stop_ai_secretary():
    """停止AI秘书服务"""
    global _ai_secretary_instance
    if _ai_secretary_instance:
        _ai_secretary_instance.stop()
        _ai_secretary_instance = None
        log.info("AI Secretary service stopped")
