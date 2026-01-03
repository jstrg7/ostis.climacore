/*
 * This source file is part of an OSTIS project. For the latest info, see
 * http://ostis.net Distributed under the MIT License (See accompanying file
 * COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#include "PathSearcher.hpp"

#include "keynodes/Keynodes.hpp"
#include "utils/NumberUtils.hpp"

PathSearcher::PathSearcher(ScMemoryContext * context)
  : m_context(context)
{
}

void PathSearcher::SearchPath(
    ScAddr const & graph,
    ScAddr const & startNode,
    ScAddr const & endNode,
    ConnectorTemplateInfo const & connectorTemplateInfo,
    WeightTemplateInfo const & weightTemplateInfo,
    PathInfo & pathInfo) const
{
  ScAddrQueue vertexesToCheck;
  ScAddrToValueUnorderedMap<unsigned> pathLengthToVertexes;
  pathLengthToVertexes[startNode] = 0;
  ScAddrToValueUnorderedMap<ScAddrVector> pathToVertexVertexes;
  ScAddrToValueUnorderedMap<ScAddrVector> pathToVertexConnectors;

  vertexesToCheck.emplace(startNode);

  while (!vertexesToCheck.empty())
  {
    ScAddr const & currentVertex = vertexesToCheck.front();
    vertexesToCheck.pop();

    ScAddrToValueUnorderedMap<ConnectorInfo> neighborsWithConnectorsInfo;
    GetNeighborsWithConnectorsInfo(
        graph, currentVertex, connectorTemplateInfo, weightTemplateInfo, neighborsWithConnectorsInfo);

    for (auto const & neighborWithPathLength : neighborsWithConnectorsInfo)
    {
      ScAddr const & neighbor = neighborWithPathLength.first;
      ScAddr const & connector = neighborWithPathLength.second.addr;
      unsigned const connectorWeight = neighborWithPathLength.second.weight;

      unsigned newPathLength = pathLengthToVertexes[currentVertex] + connectorWeight;
      if (pathLengthToVertexes.find(neighbor) == pathLengthToVertexes.cend()
          || newPathLength < pathLengthToVertexes[neighbor])
      {
        pathLengthToVertexes[neighbor] = newPathLength;

        pathToVertexVertexes[neighbor] = pathToVertexVertexes[currentVertex];
        pathToVertexVertexes[neighbor].emplace_back(neighbor);

        pathToVertexConnectors[neighbor] = pathToVertexConnectors[currentVertex];
        pathToVertexConnectors[neighbor].emplace_back(connector);

        vertexesToCheck.emplace(neighbor);
      }
    }
  }

  if (pathLengthToVertexes.find(endNode) == pathLengthToVertexes.end())
    SC_THROW_EXCEPTION(utils::ExceptionItemNotFound, "Target vertex not reached");

  pathInfo.length = pathLengthToVertexes[endNode];
  pathInfo.vertexes.clear();
  pathInfo.vertexes.emplace_back(startNode);
  pathInfo.vertexes.insert(
      pathInfo.vertexes.end(), pathToVertexVertexes[endNode].begin(), pathToVertexVertexes[endNode].end());

  pathInfo.connectors = pathToVertexConnectors[endNode];
}

void PathSearcher::GetNeighborsWithConnectorsInfo(
    ScAddr const & graph,
    ScAddr const & startNode,
    ConnectorTemplateInfo const & connectorTemplateInfo,
    WeightTemplateInfo const & weightTemplateInfo,
    ScAddrToValueUnorderedMap<ConnectorInfo> & neighborsWithConnectorsInfo) const
{
  ScTemplateParams connectorTemplateParams;
  connectorTemplateParams.Add(connectorTemplateInfo.connectorStartVariable, startNode);
  ScTemplate connectorTemplate;
  m_context->BuildTemplate(connectorTemplate, connectorTemplateInfo.templateAddr, connectorTemplateParams);

  m_context->SearchByTemplate(
      connectorTemplate,
      [&](ScTemplateResultItem const & item)
      {
        ScAddr const & connector = item[connectorTemplateInfo.connectorVariable];

        ScAddr const & neighbor = item[connectorTemplateInfo.connectorEndVariable];
        unsigned const connectorWeight = GetConnectorWeight(connector, weightTemplateInfo);

        if (neighborsWithConnectorsInfo.find(neighbor) == neighborsWithConnectorsInfo.cend()
            || neighborsWithConnectorsInfo[neighbor].weight > connectorWeight)
          neighborsWithConnectorsInfo[neighbor] = {connector, connectorWeight};
      },
      [this, &graph](ScAddr const & elementAddr) -> bool
      {
        return m_context->CheckConnector(graph, elementAddr, ScType::ConstPermPosArc);
      });
}

unsigned PathSearcher::GetConnectorWeight(ScAddr const & connector, WeightTemplateInfo const & weightTemplateInfo) const
{
  ScTemplateParams connectorWeightTemplateParams;
  connectorWeightTemplateParams.Add(weightTemplateInfo.measuredObjectVariable, connector);
  ScTemplate connectorWeightTemplate;
  m_context->BuildTemplate(connectorWeightTemplate, weightTemplateInfo.templateAddr, connectorWeightTemplateParams);

  unsigned weight;
  bool isFound = false;
  m_context->SearchByTemplateInterruptibly(
      connectorWeightTemplate,
      [this, &isFound, &weightTemplateInfo, &weight](ScTemplateResultItem const & item) -> ScTemplateSearchRequest
      {
        isFound = true;

        weight = GetNumberValue(item[weightTemplateInfo.numberVariable]);

        return ScTemplateSearchRequest::STOP;
      });

  if (!isFound)
    SC_THROW_EXCEPTION(utils::ExceptionItemNotFound, "Connector " << connector.Hash() << " weight is not found");

  return weight;
}

unsigned PathSearcher::GetNumberValue(ScAddr const & number) const
{
  ScIterator5Ptr idtfsIterator = m_context->CreateIterator5(
      number, ScType::ConstCommonArc, ScType::ConstNodeLink, ScType::ConstPermPosArc, Keynodes::nrel_idtf);
  while (idtfsIterator->Next())
  {
    ScAddr const & idtfLink = idtfsIterator->Get(2);
    std::string idtfString;
    m_context->GetLinkContent(idtfLink, idtfString);
    if (!utils::NumberUtils::IsPositiveInteger(idtfString))
      continue;

    unsigned numericValue;
    try
    {
      numericValue = std::stoi(idtfString.c_str());
    }
    catch (std::invalid_argument const & exception)
    {
      SC_LOG_WARNING("Error during idtf to number conversion: " << exception.what());
    }
    catch (std::out_of_range const & exception)
    {
      SC_LOG_WARNING("Error during idtf to number conversion: " << exception.what());
    }
    return numericValue;
  }

  SC_THROW_EXCEPTION(utils::ExceptionItemNotFound, "Number " << number.Hash() << " numeric idtf is not found");
}
