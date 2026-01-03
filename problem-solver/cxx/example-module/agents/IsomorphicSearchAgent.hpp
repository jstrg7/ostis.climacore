/*
 * This source file is part of an OSTIS project. For the latest info, see
 * http://ostis.net Distributed under the MIT License (See accompanying file
 * COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#pragma once

#include <sc-memory/sc_agent.hpp>

class IsomorphicSearchAgent : public ScActionInitiatedAgent
{
public:
  IsomorphicSearchAgent();

  ScAddr GetActionClass() const override;

  ScResult DoProgram(ScAction & action) override;

  void FormSearchResults(ScAddr const & scTemplateNode, ScStructure & result);

  void ClearPreviousSearchResults(ScAddr const & scTemplate);

  ScAddr FormNewResultsSetConstruction(ScAddr const & scTemplate, ScStructure & result);

  ScAddr EmplaceItemElementsInStructure(ScTemplateSearchResultItem const & item);
};
