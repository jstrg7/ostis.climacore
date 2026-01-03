/*
 * This source file is part of an OSTIS project. For the latest info, see
 * http://ostis.net Distributed under the MIT License (See accompanying file
 * COPYING.MIT or copy at http://opensource.org/licenses/MIT)
 */

#pragma once

#include "sc-memory/sc_memory.hpp"

#include "data-structures/ConnectorTemplateInfo.hpp"
#include "data-structures/WeightTemplateInfo.hpp"
#include "data-structures/ConnectorInfo.hpp"
#include "data-structures/PathInfo.hpp"

class PathSearcher
{
public:
  explicit PathSearcher(ScMemoryContext * context);

  void SearchPath(
      ScAddr const & graph,
      ScAddr const & startNode,
      ScAddr const & endNode,
      ConnectorTemplateInfo const & connectorTemplateInfo,
      WeightTemplateInfo const & weightTemplateInfo,
      PathInfo & pathInfo) const;

private:
  ScMemoryContext * m_context;

  void GetNeighborsWithConnectorsInfo(
      ScAddr const & graph,
      ScAddr const & startNode,
      ConnectorTemplateInfo const & connectorTemplateInfo,
      WeightTemplateInfo const & weightTemplateInfo,
      ScAddrToValueUnorderedMap<ConnectorInfo> & neighborsWithConnectorsInfo) const;

  unsigned GetConnectorWeight(ScAddr const & connector, WeightTemplateInfo const & weightTemplateInfo) const;

  unsigned GetNumberValue(ScAddr const & number) const;
};
