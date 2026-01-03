/*
 * This source file is part of an OSTIS project. For the latest info, see
 * http://ostis.net Distributed under the MIT License (See accompanying file
 * COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#include "PathSearchAgent.hpp"

#include <sc-memory/sc_memory.hpp>
#include <sc-memory/sc_stream.hpp>

#include "keynodes/Keynodes.hpp"

#include "searcher/PathSearcher.hpp"
#include "utils/TemplateUtils.hpp"
#include "utils/NumberUtils.hpp"

using namespace utils;

PathSearchAgent::PathSearchAgent()
{
  m_logger = utils::ScLogger(utils::ScLogger::ScLogType::File, "logs/PathSearchAgent.log", utils::ScLogLevel::Debug);
}

ScAddr PathSearchAgent::GetActionClass() const
{
  return Keynodes::action_search_minimum_path;
}

ScResult PathSearchAgent::DoProgram(ScAction & action)
{
  auto const & [graph, startNode, endNode, connectorTemplateAddr, connectorWeightTemplateAddr] =
      action.GetArguments<5>();

  if (!graph.IsValid())
  {
    m_logger.Error("Graph argument is not found");
    return action.FinishWithError();
  }

  if (!startNode.IsValid())
  {
    m_logger.Error("Start node argument is not found");
    return action.FinishWithError();
  }

  if (!endNode.IsValid())
  {
    m_logger.Error("End node argument is not found");
    return action.FinishWithError();
  }

  if (!connectorTemplateAddr.IsValid())
  {
    m_logger.Error("Connector template argument is not found");
    return action.FinishWithError();
  }

  if (!connectorWeightTemplateAddr.IsValid())
  {
    m_logger.Error("Connector weight template argument is not found");
    return action.FinishWithError();
  }

  if (startNode == endNode)
  {
    m_logger.Error("Start and end nodes should not match");
    return action.FinishWithError();
  }

  try
  {
    ConnectorTemplateInfo connectorTemplateInfo;
    utils::TemplateUtils::GetConnectorTemplateInfo(m_context, connectorTemplateAddr, connectorTemplateInfo);

    WeightTemplateInfo weightTemplateInfo;
    utils::TemplateUtils::GetWeightTemplateInfo(m_context, connectorWeightTemplateAddr, weightTemplateInfo);

    PathInfo pathInfo;

    PathSearcher searcher(&m_context);
    searcher.SearchPath(graph, startNode, endNode, connectorTemplateInfo, weightTemplateInfo, pathInfo);

    ScStructure const & result = FormResult(pathInfo, connectorTemplateInfo, weightTemplateInfo);
    action.SetResult(result);
  }
  catch (ScException const & exception)
  {
    m_logger.Error(exception.Message());
    return action.FinishWithError();
  }

  return action.FinishSuccessfully();
}

ScStructure PathSearchAgent::FormResult(
    PathInfo const & pathInfo,
    ConnectorTemplateInfo const & connectorTemplateInfo,
    WeightTemplateInfo const & weightTemplateInfo) const
{
  ScStructure resultStructure = m_context.GenerateStructure();
  ScStructure pathStructure = m_context.GenerateStructure();

  ScAddrVector const & pathVertexes = pathInfo.vertexes;
  ScAddrVector const & pathConnectors = pathInfo.connectors;

  auto connectorsIt = pathConnectors.begin();
  for (auto vertexesIt = pathVertexes.begin() + 1; vertexesIt != pathVertexes.end(); ++vertexesIt)
  {
    ScAddr const & first = *(vertexesIt - 1);
    ScAddr const & second = *vertexesIt;

    ScAddr const & connector = *connectorsIt;

    AddConnectionIntoStructure(first, second, connector, connectorTemplateInfo, pathStructure);

    ++connectorsIt;
  }

  AddPathWeightIntoStructure(pathStructure, weightTemplateInfo, pathInfo.length, resultStructure);

  return resultStructure;
}

void PathSearchAgent::AddConnectionIntoStructure(
    ScAddr const & first,
    ScAddr const & second,
    ScAddr const & connector,
    ConnectorTemplateInfo const & connectorTemplateInfo,
    ScStructure & structure) const
{
  ScTemplateParams connectorTemplateParams;
  connectorTemplateParams.Add(connectorTemplateInfo.connectorStartVariable, first);
  connectorTemplateParams.Add(connectorTemplateInfo.connectorEndVariable, second);
  connectorTemplateParams.Add(connectorTemplateInfo.connectorVariable, connector);

  ScTemplate connectorTemplate;
  m_context.BuildTemplate(connectorTemplate, connectorTemplateInfo.templateAddr, connectorTemplateParams);

  bool isFound = false;

  m_context.SearchByTemplateInterruptibly(
      connectorTemplate,
      [&isFound, &structure](ScTemplateResultItem const & item) -> ScTemplateSearchRequest
      {
        isFound = true;

        structure << item;

        return ScTemplateSearchRequest::STOP;
      });

  if (!isFound)
    SC_THROW_EXCEPTION(utils::ExceptionItemNotFound, "PathSearchAgent: result creation failed");
}

void PathSearchAgent::AddPathWeightIntoStructure(
    ScAddr const & pathAddr,
    WeightTemplateInfo const & weightTemplateInfo,
    unsigned const length,
    ScStructure & structure) const
{
  ScAddr const & numberAddr = utils::NumberUtils::ResolveNumber(m_context, length);

  ScTemplateParams connectorTemplateParams;
  connectorTemplateParams.Add(weightTemplateInfo.measuredObjectVariable, pathAddr);
  connectorTemplateParams.Add(weightTemplateInfo.numberVariable, numberAddr);

  ScTemplate connectorWeightTemplate;
  m_context.BuildTemplate(connectorWeightTemplate, weightTemplateInfo.templateAddr, connectorTemplateParams);
  ScTemplateGenResult genResult;
  m_context.GenerateByTemplate(connectorWeightTemplate, genResult);

  structure << genResult;
}
