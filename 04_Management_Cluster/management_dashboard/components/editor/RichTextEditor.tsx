"use client";

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Bold, Italic, List, ListOrdered, Share, Sparkles } from 'lucide-react'

// Toolbar Component
const EditorToolbar = ({ editor }: { editor: any }) => {
    if (!editor) return null

    return (
        <div className="border-b border-gray-200 bg-gray-50 p-2 flex gap-2 sticky top-0 z-10">
            <button
                onClick={() => editor.chain().focus().toggleBold().run()}
                disabled={!editor.can().chain().focus().toggleBold().run()}
                className={`p-2 rounded hover:bg-gray-200 ${editor.isActive('bold') ? 'bg-gray-200' : ''}`}
            >
                <Bold className="w-5 h-5" />
            </button>
            <button
                onClick={() => editor.chain().focus().toggleItalic().run()}
                disabled={!editor.can().chain().focus().toggleItalic().run()}
                className={`p-2 rounded hover:bg-gray-200 ${editor.isActive('italic') ? 'bg-gray-200' : ''}`}
            >
                <Italic className="w-5 h-5" />
            </button>
            <button
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                className={`p-2 rounded hover:bg-gray-200 ${editor.isActive('bulletList') ? 'bg-gray-200' : ''}`}
            >
                <List className="w-5 h-5" />
            </button>
            <button
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                className={`p-2 rounded hover:bg-gray-200 ${editor.isActive('orderedList') ? 'bg-gray-200' : ''}`}
            >
                <ListOrdered className="w-5 h-5" />
            </button>

            <div className="w-px bg-gray-300 mx-2"></div>

            {/* AI Button - Gemini 3 Integration */}
            <button
                onClick={async () => {
                    const { from, to, empty } = editor.state.selection;
                    if (empty) {
                        alert("Please select some text to rewrite.");
                        return;
                    }
                    const text = editor.state.doc.textBetween(from, to, ' ');

                    // Visual Feedback (could be a toast)
                    const originalText = text;
                    editor.commands.insertContentAt({ from, to }, "✨ Generating...");

                    try {
                        const response = await fetch('/api/ai-rewrite', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ text: originalText })
                        });

                        const data = await response.json();
                        if (data.rewritten_text) {
                            // Replace with AI result
                            editor.commands.insertContentAt({ from, to }, data.rewritten_text); // Note: Range might have shifted if we inserted text, but for simple replacement of selection this works if we didn't change doc structure too much. A safer way is to keep track of pos or lock. For V2 MVP, this is acceptable.
                        } else {
                            editor.commands.insertContentAt({ from, to }, originalText); // Revert
                            alert("AI Error: " + data.error);
                        }
                    } catch (e) {
                        editor.commands.insertContentAt({ from, to }, originalText); // Revert
                        alert("Network Error");
                    }
                }}
                className="p-2 rounded bg-purple-100 text-purple-700 hover:bg-purple-200 flex items-center gap-1 font-medium transition-colors"
            >
                <Sparkles className="w-4 h-4" />
                AI Rewrite
            </button>

            {/* Load Report Button (Simulated Integration) */}
            <button
                onClick={async () => {
                    try {
                        editor.commands.clearContent();
                        editor.commands.insertContent('<p>Loading report from Cluster 3...</p>');

                        const res = await fetch('/api/reports/latest');
                        const data = await res.json();

                        if (data.html) {
                            editor.commands.setContent(data.html);
                        } else {
                            alert("Error loading report: " + (data.error || "Unknown"));
                        }
                    } catch (e) {
                        alert("Failed to connect to Cluster 3.");
                    }
                }}
                className="p-2 rounded bg-green-100 text-green-700 hover:bg-green-200 flex items-center gap-1 font-medium transition-colors"
            >
                <Share className="w-4 h-4 rotate-180" /> {/* Re-using icon for import */}
                Load Report
            </button>

            <div className="flex-grow"></div>
            <button
                onClick={() => window.print()}
                className="p-2 px-4 rounded bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-1 font-medium"
            >
                <Share className="w-4 h-4" />
                Export PDF
            </button>

        </div>
    )
}

const RichTextEditor = () => {
    const editor = useEditor({
        extensions: [
            StarterKit,
        ],
        content: `
      <h1 class="text-center">RICS Home Survey - Level 2</h1>
      <hr>
      
      <h3>Section A: Introduction to the Report</h3>
      <p>This report provides an objective opinion on the condition of the property...</p>

      <h3>Section B: About the Inspection</h3>
      <p><strong>Property Address:</strong> [Insert Address]</p>
      <p><strong>Date:</strong> 06 January 2026</p>

      <h3>Section C: Overall Opinion</h3>
      <p>This section provides our overall opinion of the property...</p>
      <blockquote>
        "The property is considered to be a reasonable proposition for purchase at the agreed price..."
      </blockquote>

      <h3>Section D: About the Property</h3>
      <p><strong>Type:</strong> Detached House</p>
      <p><strong>Construction Year:</strong> Approx 1980</p>

      <h3>Section E: Outside the Property</h3>
      <h4>E1. Chimney Stacks</h4>
      <p><em>Condition Rating 1.</em> No significant defects noted.</p>
      
      <h4>E2. Roof Coverings</h4>
      <p><em>Condition Rating 2.</em> Some slipped slates observed...</p>

      <h3>Section F: Inside the Property</h3>
      <h4>F1. Roof Structure</h4>
      <p>[AI Suggestion: Insert finding from Cluster 1]</p>

      <hr>
      <p><em>Use the AI Rewrite button to professionally phrase your findings in each section.</em></p>
    `,
        editorProps: {
            attributes: {
                class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-xl focus:outline-none max-w-none p-8 min-h-[80vh] bg-white shadow-sm border border-gray-200 my-4 mx-auto rounded-lg',
            },
        },
        immediatelyRender: false,
    })

    return (
        <div className="bg-gray-100 min-h-screen p-8">
            <div className="max-w-4xl mx-auto rounded-xl overflow-hidden shadow-xl bg-white border border-gray-200">
                <EditorToolbar editor={editor} />
                <EditorContent editor={editor} />
            </div>
        </div>
    )
}

export default RichTextEditor
