/*
 * This source file is part of an OSTIS project. For the latest info, see
 * http://ostis.net Distributed under the MIT License (See accompanying file
 * COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#include "IsomorphicSearchAgent.hpp"

#include <sc-memory/sc_memory.hpp>
#include <sc-memory/sc_stream.hpp>

#include <sc-agents-common/utils/IteratorUtils.hpp>

#include "keynodes/Keynodes.hpp"

using namespace utils;

IsomorphicSearchAgent::IsomorphicSearchAgent()
{
  m_logger =
      utils::ScLogger(utils::ScLogger::ScLogType::File, "logs/IsomorphicSearchAgent.log", utils::ScLogLevel::Debug);
}

ScAddr IsomorphicSearchAgent::GetActionClass() const
{
  return Keynodes::action_search_isomorphic_structures;
}

ScResult IsomorphicSearchAgent::DoProgram(ScAction & action)
{
  auto const & [scTemplateNode] = action.GetArguments<1>();

  if (!scTemplateNode.IsValid())
  {
    m_logger.Error("Template argument is not found");
    return action.FinishWithError();
  }

  ScStructure result = m_context.GenerateStructure();
  try
  {
    FormSearchResults(scTemplateNode, result);
  }
  catch (ScException const & exception)
  {
    m_logger.Error(exception.Message());
    return action.FinishWithError();
  }

  action.SetResult(result);
  return action.FinishSuccessfully();
}

void IsomorphicSearchAgent::FormSearchResults(ScAddr const & scTemplateNode, ScStructure & result)
{
  ClearPreviousSearchResults(scTemplateNode);

  ScTemplate scTemplate;
  m_context.BuildTemplate(scTemplate, scTemplateNode);

  ScAddr const & resultsSet = FormNewResultsSetConstruction(scTemplateNode, result);

  ScAddrVector searchResults;
  m_context.SearchByTemplate(
      scTemplate,
      [&searchResults, this](ScTemplateSearchResultItem const & item)
      {
        searchResults.push_back(EmplaceItemElementsInStructure(item));
      });

  if (searchResults.empty())
  {
    ScAddr const & membershipArc =
        m_context.GenerateConnector(ScType::ConstPermPosArc, Keynodes::empty_set, resultsSet);
    result << membershipArc << Keynodes::empty_set;
    m_logger.Debug("Structures have not been found");
  }
  else
  {
    for (auto const & resultAddr : searchResults)
    {
      ScAddr const & membershipArc = m_context.GenerateConnector(ScType::ConstPermPosArc, resultsSet, resultAddr);
      result << membershipArc << resultAddr;
    }
    m_logger.Debug("Structures have been found");
  }
}

void IsomorphicSearchAgent::ClearPreviousSearchResults(ScAddr const & scTemplateNode)
{
  ScIterator5Ptr previousResultsStructuresSetsIterator = m_context.CreateIterator5(
      scTemplateNode, ScType::ConstCommonArc, ScType::ConstNode, ScType::ConstPermPosArc, Keynodes::nrel_search_result);
  while (previousResultsStructuresSetsIterator->Next())
  {
    ScIterator3Ptr previousResultsSetElementsIterator = m_context.CreateIterator3(
        previousResultsStructuresSetsIterator->Get(2), ScType::ConstPermPosArc, ScType::ConstNodeStructure);
    while (previousResultsSetElementsIterator->Next())
      m_context.EraseElement(previousResultsSetElementsIterator->Get(2));

    m_context.EraseElement(previousResultsStructuresSetsIterator->Get(1));
    m_context.EraseElement(previousResultsStructuresSetsIterator->Get(2));
  }
}

ScAddr IsomorphicSearchAgent::FormNewResultsSetConstruction(ScAddr const & scTemplateNode, ScStructure & result)
{
  ScAddr const & resultsSetTuple = m_context.GenerateNode(ScType::ConstNodeTuple);
  ScAddr const & searchResultRelationPair =
      m_context.GenerateConnector(ScType::ConstCommonArc, scTemplateNode, resultsSetTuple);
  ScAddr const & relationMembershipArc =
      m_context.GenerateConnector(ScType::ConstPermPosArc, Keynodes::nrel_search_result, searchResultRelationPair);

  result << resultsSetTuple << searchResultRelationPair << relationMembershipArc;
  return resultsSetTuple;
}

ScAddr IsomorphicSearchAgent::EmplaceItemElementsInStructure(ScTemplateSearchResultItem const & item)
{
  ScAddr const & searchResultStructure = m_context.GenerateNode(ScType::ConstNodeStructure);

  size_t const searchResultItemSize = item.Size();
  for (size_t elementIndex = 0; elementIndex < searchResultItemSize; elementIndex++)
    m_context.GenerateConnector(ScType::ConstPermPosArc, searchResultStructure, item[elementIndex]);

  return searchResultStructure;
}
