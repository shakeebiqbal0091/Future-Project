export function AgentCard({ agent }: AgentCardProps) {
  const { handleInstall } = useAgents()
  const [showPreview, setShowPreview] = useState(false)

  const formatPrice = (price: number) => {
    if (price === 0) return 'Free'
    if (price < 100) return `$${price}`
    return `$${(price / 100).toFixed(2)}`
  }

  const getButtonText = () => {
    if (agent.is_installed) return 'Installed'
    return 'Install'
  }

  const getButtonVariant = () => {
    if (agent.is_installed) return 'outline'
    return 'primary'
  }

  const handleInstallClick = async () => {
    if (!agent.is_installed) {
      await handleInstall(agent.id)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow">
      <div className="relative">
        {agent.featured && (
          <div className="absolute top-4 right-4 bg-yellow-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
            Featured
          </div>
        )}

        {agent.image_url && (
          <img
            src={agent.image_url}
            alt={agent.name}
            className="w-full h-48 object-cover rounded-t-lg"
          />
        )}
      </div>

      <div className="p-6">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-1">{agent.name}</h3>
            <p className="text-sm text-gray-600">{agent.description}</p>
          </div>
          <div className="ml-4 flex-shrink-0">
            <Button
              size="sm"
              variant={getButtonVariant()}
              onClick={handleInstallClick}
              disabled={agent.is_installed}
              className="w-full"
            >
              {getButtonText()}
            </Button>
          </div>
        </div>

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <StarIcon className="w-4 h-4 text-yellow-500" />
            <span className="font-medium">{agent.rating}</span>
            <span className="text-gray-500">({agent.reviews} reviews)</span>
            <Tooltip content="Average rating based on user reviews">
              <span className="text-xs text-gray-400 mx-1">•</span>
            </Tooltip>
            <ClockIcon className="w-4 h-4 text-gray-400" />
            <span className="text-gray-500">Created by</span>
            <span className="font-medium">{agent.created_by.name}</span>
            <Tooltip content="Click to view author profile">
              <span className="text-xs text-gray-400 mx-1">•</span>
            </Tooltip>
          </div>

          <div className="flex items-center space-x-2 font-semibold text-gray-900">
            {formatPrice(agent.price)}
            <Tooltip content="One-time purchase cost">
              <span className="text-xs text-gray-400">•</span>
            </Tooltip>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
            {agent.category}
          </span>

          {agent.tags.map((tag) => (
            <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
              #{tag}
            </span>
          ))}

          {agent.is_installed && (
            <Tooltip content="This agent is already installed in your workspace">
              <CheckCircleIcon className="w-4 h-4 text-green-500" />
            </Tooltip>
          )}
        </div>

        <div className="mt-4">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowPreview(!showPreview)}
            className="w-full text-left justify-start flex items-center space-x-2"
          >
            <span>{showPreview ? 'Hide Preview' : 'Show Preview'}</span>
            <Tooltip content="View more details about this agent">
              <span className="text-xs text-gray-400">(?)</span>
            </Tooltip>
          </Button>
        </div>

        {showPreview && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <strong>Preview:</strong>
              <span>This agent can help with {agent.description.toLowerCase()}</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Button size="sm" variant="outline" className="flex-1">
                <span className="flex items-center space-x-2">
                  <span className="w-4 h-4 text-gray-400">[&#9654;]</span>
                  <span>Test Agent</span>
                </span>
              </Button>
              <Button size="sm" variant="outline" className="flex-1">
                <span className="flex items-center space-x-2">
                  <span className="w-4 h-4 text-gray-400">[DOC]</span>
                  <span>View Docs</span>
                </span>
              </Button>
            </div>

            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <span>Requires: Claude API key</span>
              <span className="text-xs text-gray-400">•</span>
              <span>Compatibility: All platforms</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}