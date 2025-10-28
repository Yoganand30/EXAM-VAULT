import { useEffect, useState } from "react";
import { scrutinyGetResults, scrutinyGetSummary } from "../api/auth";

export default function ScrutinyDashboard() {
  const [summary, setSummary] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedResult, setSelectedResult] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const loadScrutinyData = async () => {
    try {
      setLoading(true);
      const [summaryResponse, resultsResponse] = await Promise.all([
        scrutinyGetSummary(),
        scrutinyGetResults()
      ]);
      
      setSummary(summaryResponse.data);
      setResults(resultsResponse.data.results || []);
    } catch (error) {
      console.error("Error loading scrutiny data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScrutinyData();
  }, []);

  const getQualityColor = (status) => {
    switch (status) {
      case "excellent": return "text-green-600 bg-green-100";
      case "good": return "text-blue-600 bg-blue-100";
      case "fair": return "text-yellow-600 bg-yellow-100";
      case "poor": return "text-red-600 bg-red-100";
      default: return "text-gray-600 bg-gray-100";
    }
  };

  const getScoreColor = (score) => {
    const numScore = parseInt(score.replace('%', ''));
    if (numScore >= 80) return "text-green-600";
    if (numScore >= 60) return "text-blue-600";
    if (numScore >= 40) return "text-yellow-600";
    return "text-red-600";
  };

  const openDetailModal = (result) => {
    setSelectedResult(result);
    setShowDetailModal(true);
  };

  if (loading) {
    return (
      <div className="border p-6 rounded shadow-sm">
        <h2 className="text-2xl font-semibold text-center mb-4">Scrutiny Dashboard</h2>
        <div className="text-center">Loading scrutiny data...</div>
      </div>
    );
  }

  return (
    <div className="border p-6 rounded shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-semibold">Scrutiny Dashboard</h2>
        <button 
          onClick={loadScrutinyData}
          className="px-3 py-1 bg-blue-600 text-white rounded text-sm"
        >
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-blue-600">{summary.total_papers}</div>
            <div className="text-sm text-gray-600">Total Papers</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-green-600">{summary.average_score}%</div>
            <div className="text-sm text-gray-600">Avg Score</div>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">{summary.papers_needing_review}</div>
            <div className="text-sm text-gray-600">Need Review</div>
          </div>
          <div className="bg-red-50 p-4 rounded-lg">
            <div className="text-2xl font-bold text-red-600">{summary.plagiarism_issues}</div>
            <div className="text-sm text-gray-600">Plagiarism Issues</div>
          </div>
        </div>
      )}

      {/* Quality Distribution */}
      {summary && summary.quality_distribution && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Quality Distribution</h3>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(summary.quality_distribution).map(([quality, count]) => (
              <div key={quality} className={`p-3 rounded-lg ${getQualityColor(quality)}`}>
                <div className="text-lg font-bold">{count}</div>
                <div className="text-sm capitalize">{quality}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse border border-gray-300">
          <thead>
            <tr className="bg-gray-50">
              <th className="border border-gray-300 p-2 text-left">Subject Code</th>
              <th className="border border-gray-300 p-2 text-left">Teacher</th>
              <th className="border border-gray-300 p-2 text-left">Questions</th>
              <th className="border border-gray-300 p-2 text-left">Score</th>
              <th className="border border-gray-300 p-2 text-left">Quality</th>
              <th className="border border-gray-300 p-2 text-left">Date</th>
              <th className="border border-gray-300 p-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {results.length === 0 ? (
              <tr>
                <td colSpan="7" className="border border-gray-300 p-4 text-center text-gray-500">
                  No scrutiny results available
                </td>
              </tr>
            ) : (
              results.map((result) => (
                <tr key={result.id} className="hover:bg-gray-50">
                  <td className="border border-gray-300 p-2">
                    {result.request_info?.subject_code || 'N/A'}
                  </td>
                  <td className="border border-gray-300 p-2">
                    {result.request_info?.teacher_name || 'N/A'}
                  </td>
                  <td className="border border-gray-300 p-2">
                    {result.summary?.num_questions || 0}
                  </td>
                  <td className="border border-gray-300 p-2">
                    <span className={`font-bold ${getScoreColor(result.overall_score_display)}`}>
                      {result.overall_score_display}
                    </span>
                  </td>
                  <td className="border border-gray-300 p-2">
                    <span className={`px-2 py-1 rounded text-xs ${getQualityColor(result.quality_status)}`}>
                      {result.quality_status}
                    </span>
                  </td>
                  <td className="border border-gray-300 p-2">
                    {new Date(result.created_at).toLocaleDateString()}
                  </td>
                  <td className="border border-gray-300 p-2">
                    <button
                      onClick={() => openDetailModal(result)}
                      className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Modal */}
      {showDetailModal && selectedResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white w-[800px] max-w-[95%] rounded-lg shadow-lg p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold">Scrutiny Details</h3>
              <button 
                className="text-gray-600 hover:text-gray-800"
                onClick={() => setShowDetailModal(false)}
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="font-semibold">Subject Code:</label>
                  <div>{selectedResult.request_info?.subject_code || 'N/A'}</div>
                </div>
                <div>
                  <label className="font-semibold">Teacher:</label>
                  <div>{selectedResult.request_info?.teacher_name || 'N/A'}</div>
                </div>
                <div>
                  <label className="font-semibold">Total Questions:</label>
                  <div>{selectedResult.summary?.num_questions || 0}</div>
                </div>
                <div>
                  <label className="font-semibold">Overall Score:</label>
                  <div className={`font-bold ${getScoreColor(selectedResult.overall_score_display)}`}>
                    {selectedResult.overall_score_display}
                  </div>
                </div>
              </div>

              {/* Bloom's Taxonomy Distribution */}
              {selectedResult.summary?.bloom_distribution && (
                <div>
                  <label className="font-semibold">Bloom's Taxonomy Distribution:</label>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    {Object.entries(selectedResult.summary.bloom_distribution).map(([level, score]) => (
                      <div key={level} className="bg-gray-100 p-2 rounded">
                        <div className="text-sm font-medium capitalize">{level}</div>
                        <div className="text-lg font-bold">{Math.round(score * 100)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Difficulty Distribution */}
              {selectedResult.summary?.difficulty_distribution && (
                <div>
                  <label className="font-semibold">Difficulty Distribution:</label>
                  <div className="grid grid-cols-3 gap-2 mt-2">
                    {Object.entries(selectedResult.summary.difficulty_distribution).map(([level, count]) => (
                      <div key={level} className={`p-2 rounded ${getQualityColor(level)}`}>
                        <div className="text-sm font-medium capitalize">{level}</div>
                        <div className="text-lg font-bold">{Math.round(count * 100)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Plagiarism Analysis */}
              {selectedResult.summary?.plagiarism_analysis && (
                <div>
                  <label className="font-semibold">Plagiarism Analysis:</label>
                  <div className="mt-2 space-y-2">
                    <div className="flex justify-between">
                      <span>Plagiarism Score:</span>
                      <span className={`font-bold ${selectedResult.summary.plagiarism_analysis.plagiarism_score > 0.3 ? 'text-red-600' : 'text-green-600'}`}>
                        {Math.round(selectedResult.summary.plagiarism_analysis.plagiarism_score * 100)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Duplicate Questions:</span>
                      <span>{selectedResult.summary.plagiarism_analysis.duplicates?.length || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Similar Questions:</span>
                      <span>{selectedResult.summary.plagiarism_analysis.similar_questions?.length || 0}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {selectedResult.summary?.recommendations && selectedResult.summary.recommendations.length > 0 && (
                <div>
                  <label className="font-semibold">Recommendations:</label>
                  <ul className="mt-2 space-y-1">
                    {selectedResult.summary.recommendations.map((rec, index) => (
                      <li key={index} className="text-sm text-gray-700">• {rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tags */}
              {selectedResult.summary?.tags && selectedResult.summary.tags.length > 0 && (
                <div>
                  <label className="font-semibold">Tags:</label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selectedResult.summary.tags.map((tag, index) => (
                      <span key={index} className="px-2 py-1 bg-gray-200 rounded text-sm">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

