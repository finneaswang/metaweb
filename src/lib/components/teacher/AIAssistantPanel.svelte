<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { askTeacherAI, type StudentInfo, type TeacherAIResponse } from '$lib/apis/teacher';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let student: StudentInfo;

	const dispatch = createEventDispatcher();

	interface Message {
		role: 'user' | 'assistant';
		content: string;
		sources?: {
			conversation_count: number;
			assignment_count: number;
			date_range: string;
		};
	}

	let messages: Message[] = [];
	let question = '';
	let loading = false;

	const quickQuestions = [
		'这个学生整体情况怎么样？',
		'TA 有什么薄弱环节？',
		'TA 最近进步了吗？',
		'需要我重点关注什么？'
	];

	const ask = async (q?: string) => {
		const questionText = q || question;
		if (!questionText.trim()) {
			toast.error('请输入问题');
			return;
		}

		// Add user message
		messages = [...messages, { role: 'user', content: questionText }];
		question = '';
		loading = true;

		try {
			const response: TeacherAIResponse = await askTeacherAI(localStorage.token, {
				student_id: student.id,
				question: questionText
			});

			// Add assistant message
			messages = [
				...messages,
				{
					role: 'assistant',
					content: response.answer,
					sources: {
						conversation_count: response.data_sources.conversation_count,
						assignment_count: response.data_sources.assignment_count,
						date_range: response.data_sources.date_range
					}
				}
			];
		} catch (error) {
			toast.error(`AI 回答失败: ${error}`);
			// Remove the user message if failed
			messages = messages.slice(0, -1);
		} finally {
			loading = false;
		}
	};

	const handleKeypress = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			ask();
		}
	};
</script>

<!-- Modal Overlay -->
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-end z-50" on:click={() => dispatch('close')}>
	<!-- Panel -->
	<div 
		class="bg-white dark:bg-gray-900 h-full w-full md:w-2/3 lg:w-1/2 shadow-2xl flex flex-col"
		on:click|stopPropagation
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-6 py-4 border-b dark:border-gray-800">
			<div>
				<h2 class="text-xl font-semibold dark:text-gray-100">AI 助手</h2>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					关于学生：{student.name}
				</p>
			</div>
			<button
				on:click={() => dispatch('close')}
				class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Quick Questions -->
		<div class="px-6 py-4 border-b dark:border-gray-800 bg-gray-50 dark:bg-gray-950">
			<p class="text-xs text-gray-500 dark:text-gray-400 mb-2">快捷问题：</p>
			<div class="flex flex-wrap gap-2">
				{#each quickQuestions as q}
					<button
						on:click={() => ask(q)}
						disabled={loading}
						class="px-3 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{q}
					</button>
				{/each}
			</div>
		</div>

		<!-- Messages -->
		<div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
			{#if messages.length === 0}
				<div class="text-center py-12">
					<p class="text-gray-400 dark:text-gray-500">开始提问关于这个学生的问题...</p>
				</div>
			{:else}
				{#each messages as msg}
					{#if msg.role === 'user'}
						<div class="flex justify-end">
							<div class="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-[80%]">
								<p class="text-sm">{msg.content}</p>
							</div>
						</div>
					{:else}
						<div class="flex justify-start">
							<div class="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3 max-w-[90%]">
								<div class="prose prose-sm dark:prose-invert max-w-none">
									{@html msg.content.replace(/\n/g, '<br>')}
								</div>
								{#if msg.sources}
									<div class="mt-3 pt-3 border-t dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
										📊 数据来源：{msg.sources.conversation_count} 次对话，{msg.sources.assignment_count} 次作业 ({msg.sources.date_range})
									</div>
								{/if}
							</div>
						</div>
					{/if}
				{/each}
			{/if}

			{#if loading}
				<div class="flex justify-start">
					<div class="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3">
						<div class="flex items-center space-x-2">
							<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900 dark:border-gray-100"></div>
							<span class="text-sm text-gray-500">AI 正在思考...</span>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Input -->
		<div class="px-6 py-4 border-t dark:border-gray-800">
			<div class="flex items-end space-x-2">
				<textarea
					bind:value={question}
					on:keypress={handleKeypress}
					placeholder="问问关于这个学生的任何问题..."
					disabled={loading}
					rows="2"
					class="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
				/>
				<button
					on:click={() => ask()}
					disabled={loading || !question.trim()}
					class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm h-[66px]"
				>
					发送
				</button>
			</div>
			<p class="text-xs text-gray-400 dark:text-gray-500 mt-2">
				按 Enter 发送，Shift+Enter 换行
			</p>
		</div>
	</div>
</div>
